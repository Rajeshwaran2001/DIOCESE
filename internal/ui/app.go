//go:build windows

// Package ui builds the native Win32 window, tabs and forms (lxn/walk) and
// wires them to the store, config and printing packages.
package ui

import (
	"fmt"
	"os"
	"syscall"
	"time"
	"unsafe"

	"diocese-certs/internal/config"
	"diocese-certs/internal/store"

	"github.com/lxn/walk"
	. "github.com/lxn/walk/declarative"
	"github.com/lxn/win"
)

const dateLayout = "2006-01-02"

// tableFont is applied to every history TableView. A clear, slightly larger
// font makes the column headers (which inherit the control font) easy to read —
// the previous default rendered them thin and pale.
var tableFont = Font{Family: "Segoe UI", PointSize: 10}

// sectionTitle renders a large heading at the top of each panel so the user
// always knows which form they are on now that the top tabs are gone.
func sectionTitle(text string) Label {
	return Label{
		Text:      text,
		Font:      Font{Family: "Segoe UI", PointSize: 16, Bold: true},
		TextColor: walk.RGB(0x1f, 0x2d, 0x3d),
	}
}

// parseDate turns a stored "YYYY-MM-DD" string into a time.Time; on failure it
// returns today's date so the DateEdit always has something sensible.
func parseDate(s string) time.Time {
	if t, err := time.Parse(dateLayout, s); err == nil {
		return t
	}
	return time.Now()
}

// fmtDate formats a DateEdit value back to the stored string form.
func fmtDate(t time.Time) string { return t.Format(dateLayout) }

// stringTableModel is a simple read-only TableView model backed by a grid of
// pre-rendered cell strings plus a parallel slice of record IDs. Sections call
// SetRows() then PublishRowsReset() to refresh.
type stringTableModel struct {
	walk.TableModelBase
	ids  []int64
	rows [][]string
}

func (m *stringTableModel) RowCount() int { return len(m.rows) }

func (m *stringTableModel) Value(row, col int) interface{} {
	if row < 0 || row >= len(m.rows) || col < 0 || col >= len(m.rows[row]) {
		return ""
	}
	return m.rows[row][col]
}

// SetRows replaces the data and notifies the view.
func (m *stringTableModel) SetRows(ids []int64, rows [][]string) {
	m.ids = ids
	m.rows = rows
	m.PublishRowsReset()
}

// IDAt returns the record ID for a view row, or 0 if out of range.
func (m *stringTableModel) IDAt(row int) int64 {
	if row < 0 || row >= len(m.ids) {
		return 0
	}
	return m.ids[row]
}

// App holds shared, process-wide state.
type App struct {
	cfg *config.Config
	db  *store.DB
	mw  *walk.MainWindow

	death    *deathSection
	marriage *marriageSection
	baptism  *baptismSection
	settings *settingsSection

	// Sidebar navigation: the swappable content panels and their nav buttons,
	// indexed so navTo can show one panel and highlight its button.
	panels      []*walk.Composite
	navBtns     []*walk.PushButton
	contentArea *walk.Composite // parent of the panels; suspended during swaps

	// Nav button fonts are created once and reused. Creating a walk.Font on every
	// click allocates a GDI handle that is never freed, which leaks handles and
	// makes navigation progressively laggy.
	navFontRegular *walk.Font
	navFontBold    *walk.Font

	current int // index of the panel currently shown

	// origWndProc is the window's original procedure, saved when we subclass it
	// to implement custom (borderless) window chrome (see installCustomChrome).
	origWndProc uintptr

	// Custom title-bar buttons (owner-drawn with the Windows theme).
	btnMin, btnMaxRestore, btnClose *captionButton

	// Header drag region: the title-bar composite and its label children whose
	// mouse-down starts a window drag (double-click toggles maximize). Subclassed
	// so child widgets do not swallow the caption drag.
	headerComposite *walk.Composite
	headerLabel1    *walk.Label
	headerLabel2    *walk.Label
}

// headerHeight is the height of the custom title bar / branded header, in DIPs.
// WM_NCHITTEST treats this top strip as the draggable caption.
const headerHeight = 58

// Run loads configuration, opens the database, builds the main window and runs
// the message loop. It is the single entry point called by cmd/diocesecerts.
func Run() {
	// Load config (creates a default config.json + data folder if first run).
	// LoadConfig always returns a usable (non-nil) config even on error.
	cfg, err := config.LoadConfig()
	if err != nil {
		walk.MsgBox(nil, "Configuration error",
			"Could not load or create configuration:\n\n"+err.Error(),
			walk.MsgBoxIconError)
		// Continue with the default so the user can fix the path in Settings.
	}

	app := &App{cfg: cfg}

	// Open the database. If the configured data path is bad, tell the user and
	// let them fix it via Settings rather than crashing.
	if err := app.openDB(); err != nil {
		walk.MsgBox(nil, "Database error",
			"Could not open the database at:\n"+cfg.DBPath()+
				"\n\n"+err.Error()+
				"\n\nThe program will start so you can choose a different data folder in Settings.",
			walk.MsgBoxIconWarning)
	}

	// Build the section controllers.
	app.death = newDeathSection(app)
	app.marriage = newMarriageSection(app)
	app.baptism = newBaptismSection(app)
	app.settings = newSettingsSection(app)

	// The four content panels, in nav order. Each section renders its body into
	// a Composite whose visibility we toggle from the sidebar.
	app.panels = make([]*walk.Composite, 4)
	app.navBtns = make([]*walk.PushButton, 4)

	// Build the main window (Create, not Run, so we can initialise data first).
	//
	// Layout: an HBox with a fixed-width sidebar on the left (a column of nav
	// buttons) and a content area on the right that stacks the four panels and
	// shows one at a time. walk has no native sidebar widget, so this is the
	// idiomatic way to build one.
	if err := (MainWindow{
		AssignTo: &app.mw,
		Title:    "Diocese of Madurai Ramnad — Certificate Manager",
		MinSize:  Size{Width: 1000, Height: 700},
		Size:     Size{Width: 1180, Height: 780},
		// Double-buffer the whole window so resizes and monitor/DPI switches
		// repaint in one pass instead of flickering.
		DoubleBuffering: true,
		// Outer VBox: a full-width branded header bar on top, then the body
		// (sidebar + content) below. The header keeps the app branded even when
		// maximized, where Windows pushes the OS title bar off the top edge.
		Layout: VBox{MarginsZero: true, SpacingZero: true},
		Children: []Widget{
			app.headerBar(),
			Composite{
				StretchFactor: 1,
				Layout:        HBox{MarginsZero: true, SpacingZero: true},
				Children: []Widget{
					app.sidebar(),
					Composite{
						AssignTo:        &app.contentArea,
						StretchFactor:   1,
						DoubleBuffering: true,
						// Uniform background so the areas not covered by a form (top,
						// right, bottom) read as one clean surface instead of a varying
						// grey, and transient gaps during a panel swap are invisible.
						Background: SolidColorBrush{Color: contentBG},
						Layout:     VBox{Margins: Margins{Left: 16, Top: 16, Right: 16, Bottom: 16}},
						Children: []Widget{
							app.death.Widget(&app.panels[0]),
							app.marriage.Widget(&app.panels[1]),
							app.baptism.Widget(&app.panels[2]),
							app.settings.Widget(&app.panels[3]),
						},
					},
				},
			},
		},
	}).Create(); err != nil {
		walk.MsgBox(nil, "Startup error", err.Error(), walk.MsgBoxIconError)
		os.Exit(1)
	}

	// Apply a comfortable default font for clerical readability.
	if font, err := walk.NewFont("Segoe UI", 10, 0); err == nil {
		app.mw.SetFont(font)
	}

	// Pre-create the nav button fonts once (reused by navTo).
	app.navFontRegular, _ = walk.NewFont("Segoe UI", 11, 0)
	app.navFontBold, _ = walk.NewFont("Segoe UI", 11, walk.FontBold)

	// Replace the OS frame with custom (borderless) chrome: our header bar
	// becomes the title bar with its own min/max/close buttons and is draggable.
	// This lets the window truly fill the screen when maximized while keeping the
	// window controls always visible — the native frame cannot do both.
	app.installCustomChrome()
	app.installHeaderDrag()

	// Show the first panel by default.
	app.current = -1
	app.navTo(0)

	// Initial data load into the history tables (db may be nil if path bad).
	app.refreshAll()

	// Open maximized by default, once the message loop is running. Doing this
	// from inside Synchronize (rather than before Run) guarantees the window is
	// shown maximized AND activated/focused.
	app.mw.Synchronize(func() {
		h := app.mw.Handle()
		win.ShowWindow(h, win.SW_SHOWMAXIMIZED)
		win.SetForegroundWindow(h)
		app.syncMaxRestoreGlyph()
	})

	app.mw.Run()
}

// navItems is the ordered list of sidebar entries (label shown on the button).
var navItems = []string{"Death", "Marriage", "Baptism", "Settings"}

// Palette shared by the header and sidebar.
var (
	headerBG  = walk.RGB(0x16, 0x22, 0x30) // near-black slate (top bar)
	sidebarBG = walk.RGB(0x1f, 0x2d, 0x3d) // deep slate (nav rail)
	contentBG = walk.RGB(0xF0, 0xF0, 0xF0) // content surface (matches dialog/tab grey)
	mutedText = walk.RGB(0x9f, 0xb3, 0xc8)
	whiteText = walk.RGB(0xff, 0xff, 0xff)
)

// headerBar builds the custom title bar: branding on the left, owner-drawn
// Windows-style window controls (minimize / maximize-restore / close) on the
// right. The strip itself is draggable via WM_NCHITTEST (it reports as caption).
func (a *App) headerBar() Composite {
	a.btnMin = &captionButton{app: a, kind: capMinimize, onClick: a.onMinimize}
	a.btnMaxRestore = &captionButton{app: a, kind: capMaxRestore, onClick: a.onMaxRestore,
		zoomedFn: func() bool { return win.IsZoomed(a.mw.Handle()) }}
	a.btnClose = &captionButton{app: a, kind: capClose, onClick: a.onClose}

	return Composite{
		AssignTo:        &a.headerComposite,
		MinSize:         Size{Height: headerHeight},
		MaxSize:         Size{Height: headerHeight},
		Background:      SolidColorBrush{Color: headerBG},
		DoubleBuffering: true,
		Layout:          HBox{Margins: Margins{Left: 18, Top: 0, Right: 0, Bottom: 0}, Spacing: 0},
		Children: []Widget{
			Composite{
				Layout: VBox{MarginsZero: true, SpacingZero: true},
				Children: []Widget{
					VSpacer{},
					Label{AssignTo: &a.headerLabel1, Text: "Diocese of Madurai Ramnad", TextColor: whiteText, Font: Font{Family: "Segoe UI", PointSize: 14, Bold: true}},
					Label{AssignTo: &a.headerLabel2, Text: "Certificate Manager", TextColor: mutedText, Font: Font{Family: "Segoe UI", PointSize: 9}},
					VSpacer{},
				},
			},
			HSpacer{},
			a.btnMin.declarative(),
			a.btnMaxRestore.declarative(),
			a.btnClose.declarative(),
		},
	}
}

// installHeaderDrag makes the title bar behave like a real caption: pressing
// the left button on the header (or its labels) starts a window-move, and
// double-clicking toggles maximize/restore. Child widgets in the header would
// otherwise swallow these clicks, so we subclass each one and forward the
// gesture to the main window.
func (a *App) installHeaderDrag() {
	for _, w := range []walk.Window{a.headerComposite, a.headerLabel1, a.headerLabel2} {
		if w == nil {
			continue
		}
		a.subclassDragRegion(w.Handle())
	}
}

// dragProcs keeps each drag-region's original window procedure alive, keyed by
// HWND, so the syscall callbacks can chain to it.
var dragProcs = map[win.HWND]uintptr{}

func (a *App) subclassDragRegion(h win.HWND) {
	if h == 0 {
		return
	}
	orig := win.GetWindowLongPtr(h, win.GWLP_WNDPROC)
	dragProcs[h] = orig
	win.SetWindowLongPtr(h, win.GWLP_WNDPROC, syscall.NewCallback(
		func(hwnd win.HWND, msg uint32, wParam, lParam uintptr) uintptr {
			switch msg {
			case win.WM_LBUTTONDOWN:
				// Start a native window-move loop.
				win.ReleaseCapture()
				win.SendMessage(a.mw.Handle(), win.WM_NCLBUTTONDOWN, uintptr(win.HTCAPTION), 0)
				return 0
			case win.WM_LBUTTONDBLCLK:
				a.onMaxRestore()
				return 0
			}
			return win.CallWindowProc(dragProcs[hwnd], hwnd, msg, wParam, lParam)
		}))
}

// onMinimize minimizes the window.
func (a *App) onMinimize() { win.ShowWindow(a.mw.Handle(), win.SW_MINIMIZE) }

// onMaxRestore toggles between maximized and normal.
func (a *App) onMaxRestore() {
	h := a.mw.Handle()
	if win.IsZoomed(h) {
		win.ShowWindow(h, win.SW_RESTORE)
	} else {
		win.ShowWindow(h, win.SW_SHOWMAXIMIZED)
	}
	a.syncMaxRestoreGlyph()
}

// onClose closes the window.
func (a *App) onClose() { a.mw.Close() }

// syncMaxRestoreGlyph repaints the maximize/restore button so its glyph matches
// the current window state.
func (a *App) syncMaxRestoreGlyph() {
	if a.btnMaxRestore != nil {
		a.btnMaxRestore.invalidate()
	}
}

// resizeBorder is the thickness (DIPs) of the invisible edge band that
// WM_NCHITTEST reports as a resize grip, since the window has no visible frame.
const resizeBorder = 6

// installCustomChrome turns the window into a borderless ("custom chrome")
// window: it strips WS_CAPTION (the OS title bar) while keeping WS_THICKFRAME so
// the window still resizes, snaps and truly maximizes. The subclassed window
// procedure then removes the non-client area (WM_NCCALCSIZE), provides drag and
// resize behaviour (WM_NCHITTEST) and clamps the maximized size to the work
// area so a borderless maximize does not cover the taskbar.
func (a *App) installCustomChrome() {
	h := a.mw.Handle()

	style := win.GetWindowLong(h, win.GWL_STYLE)
	style &^= win.WS_CAPTION // drop the OS title bar...
	style |= win.WS_THICKFRAME | win.WS_MINIMIZEBOX | win.WS_MAXIMIZEBOX | win.WS_SYSMENU
	win.SetWindowLong(h, win.GWL_STYLE, style)

	a.origWndProc = win.GetWindowLongPtr(h, win.GWLP_WNDPROC)
	win.SetWindowLongPtr(h, win.GWLP_WNDPROC, syscall.NewCallback(a.wndProc))

	// Recalculate the frame now that the style changed.
	win.SetWindowPos(h, 0, 0, 0, 0, 0,
		win.SWP_NOMOVE|win.SWP_NOSIZE|win.SWP_NOZORDER|win.SWP_FRAMECHANGED)
}

func (a *App) wndProc(hwnd win.HWND, msg uint32, wParam, lParam uintptr) uintptr {
	switch msg {
	case win.WM_NCCALCSIZE:
		// Returning 0 with wParam!=0 removes the entire non-client area, so the
		// client area fills the whole window — no OS title bar or borders.
		if wParam != 0 {
			return 0
		}

	case win.WM_NCHITTEST:
		return a.hitTest(hwnd, lParam)

	case win.WM_GETMINMAXINFO:
		// Clamp a (now borderless) maximize to the monitor work area so it fills
		// the screen exactly without covering the taskbar.
		mon := win.MonitorFromWindow(hwnd, win.MONITOR_DEFAULTTONEAREST)
		var mi win.MONITORINFO
		mi.CbSize = uint32(unsafe.Sizeof(mi))
		if win.GetMonitorInfo(mon, &mi) {
			work, full := mi.RcWork, mi.RcMonitor
			mmi := (*win.MINMAXINFO)(unsafe.Pointer(lParam))
			mmi.PtMaxPosition.X = work.Left - full.Left
			mmi.PtMaxPosition.Y = work.Top - full.Top
			mmi.PtMaxSize.X = work.Right - work.Left
			mmi.PtMaxSize.Y = work.Bottom - work.Top
			mmi.PtMaxTrackSize.X = work.Right - work.Left
			mmi.PtMaxTrackSize.Y = work.Bottom - work.Top
		}
		return 0

	case win.WM_SIZE:
		// Window state may have changed (maximize/restore) — keep the glyph synced.
		a.syncMaxRestoreGlyph()
	}
	return win.CallWindowProc(a.origWndProc, hwnd, msg, wParam, lParam)
}

// hitTest implements WM_NCHITTEST for the borderless window: it reports resize
// grips along the edges, the header strip as the draggable caption, and the
// window-control buttons / rest of the client as client area.
func (a *App) hitTest(hwnd win.HWND, lParam uintptr) uintptr {
	// Screen coordinates of the cursor from lParam (low word = x, high word = y).
	sx := int32(int16(lParam & 0xFFFF))
	sy := int32(int16((lParam >> 16) & 0xFFFF))

	var rc win.RECT
	win.GetWindowRect(hwnd, &rc)

	dpi := uint32(a.mw.DPI())
	scale := func(v int) int32 { return int32(v) * int32(dpi) / 96 }
	border := scale(resizeBorder)
	header := scale(headerHeight)

	zoomed := win.IsZoomed(hwnd)

	// Resize grips (disabled while maximized, where there is nothing to resize).
	if !zoomed {
		left := sx < rc.Left+border
		right := sx >= rc.Right-border
		top := sy < rc.Top+border
		bottom := sy >= rc.Bottom-border
		switch {
		case top && left:
			return win.HTTOPLEFT
		case top && right:
			return win.HTTOPRIGHT
		case bottom && left:
			return win.HTBOTTOMLEFT
		case bottom && right:
			return win.HTBOTTOMRIGHT
		case left:
			return win.HTLEFT
		case right:
			return win.HTRIGHT
		case top:
			return win.HTTOP
		case bottom:
			return win.HTBOTTOM
		}
	}

	// The header strip (minus the control buttons on the right) is the caption,
	// so the user can drag the window by it and double-click to maximize.
	if sy < rc.Top+header {
		// Leave the three control buttons on the right as client area so they
		// remain clickable rather than starting a window drag.
		if sx < rc.Right-scale(3*captionButtonWidth) {
			return win.HTCAPTION
		}
	}
	return win.HTCLIENT
}

// sidebar builds the left navigation rail (nav buttons only; branding lives in
// the header bar now).
func (a *App) sidebar() Composite {
	btns := make([]Widget, 0, len(navItems)+2)
	btns = append(btns, VSpacer{Size: 8})

	for i, name := range navItems {
		i, name := i, name
		btns = append(btns, PushButton{
			AssignTo:  &a.navBtns[i],
			Text:      "   " + name,
			MinSize:   Size{Height: 44},
			Font:      Font{Family: "Segoe UI", PointSize: 11},
			OnClicked: func() { a.navTo(i) },
		})
	}

	btns = append(btns, VSpacer{})

	return Composite{
		MaxSize:         Size{Width: 210},
		MinSize:         Size{Width: 210},
		Background:      SolidColorBrush{Color: sidebarBG},
		DoubleBuffering: true,
		Layout:          VBox{Margins: Margins{Left: 8, Top: 0, Right: 8, Bottom: 0}, Spacing: 4},
		Children:        btns,
	}
}

// navTo shows the panel at index i and hides the rest, updating button styling
// so the active item reads as selected, skipping work if already shown.
func (a *App) navTo(i int) {
	if i == a.current {
		return
	}

	// Suspend the whole window for the swap so walk performs one relayout +
	// repaint when resumed. The nav-button font change (active indicator) is
	// inside the same suspend so the sidebar lays out once with the new bold
	// widths — doing it outside previously dropped the top button.
	//
	// Note: walk still repaints a freshly-shown panel's child controls lazily,
	// so there is a brief content-paint flash on switch. Forcing the paint
	// (RedrawWindow/UpdateWindow) was tried and made it worse, so we don't.
	a.mw.SetSuspended(true)
	for j, p := range a.panels {
		if p != nil {
			p.SetVisible(j == i)
		}
	}
	for j, b := range a.navBtns {
		if b == nil {
			continue
		}
		if j == i {
			b.SetFont(a.navFontBold)
		} else {
			b.SetFont(a.navFontRegular)
		}
	}
	a.current = i
	a.mw.SetSuspended(false)
}

// openDB closes any existing connection and opens a fresh one from config.
func (a *App) openDB() error {
	if a.db != nil {
		a.db.Close()
		a.db = nil
	}
	if err := os.MkdirAll(a.cfg.DataPath, 0o755); err != nil {
		return err
	}
	db, err := store.OpenDB(a.cfg.DBPath())
	if err != nil {
		return err
	}
	a.db = db
	return nil
}

// refreshAll reloads every history table (called on startup and after a data
// path change).
func (a *App) refreshAll() {
	if a.death != nil {
		a.death.refresh()
	}
	if a.marriage != nil {
		a.marriage.refresh()
	}
	if a.baptism != nil {
		a.baptism.refresh()
	}
}

// ----------------------------------------------------------------------------
// Small UI helpers shared by all sections
// ----------------------------------------------------------------------------

func (a *App) errorBox(title string, err error) {
	walk.MsgBox(a.mw, title, err.Error(), walk.MsgBoxIconError)
}

func (a *App) infoBox(title, msg string) {
	walk.MsgBox(a.mw, title, msg, walk.MsgBoxIconInformation)
}

// confirm shows a Yes/No box; returns true if the user clicked Yes.
func (a *App) confirm(title, msg string) bool {
	r := walk.MsgBox(a.mw, title, msg, walk.MsgBoxYesNo|walk.MsgBoxIconQuestion)
	return r == walk.DlgCmdYes
}

// requireDB ensures the database is available before an action, showing a
// friendly message otherwise.
func (a *App) requireDB() bool {
	if a.db == nil {
		walk.MsgBox(a.mw, "No database",
			"The database is not open. Please set a valid data folder in the Settings tab.",
			walk.MsgBoxIconWarning)
		return false
	}
	return true
}

// errf is a tiny helper to build errors with context.
func errf(format string, args ...interface{}) error {
	return fmt.Errorf(format, args...)
}
