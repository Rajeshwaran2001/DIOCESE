//go:build windows

package ui

import (
	"syscall"
	"unsafe"

	"github.com/lxn/walk"
	. "github.com/lxn/walk/declarative"
	"github.com/lxn/win"
)

// captionKind identifies which title-bar button to draw.
type captionKind int

const (
	capMinimize captionKind = iota
	capMaxRestore
	capClose
)

// captionButton is an owner-drawn title-bar button that renders the authentic
// Windows min/max/restore/close glyphs via the visual-style theme API, with
// real hover (hot) and pressed states — including the red close-button hover.
type captionButton struct {
	app      *App
	widget   *walk.CustomWidget
	kind     captionKind
	zoomedFn func() bool // for capMaxRestore: report whether window is maximized
	onClick  func()

	hot      bool
	pressed  bool
	tracking bool
	origProc uintptr
}

// captionButtonWidth/Height are the control sizes in DIPs (Windows title-bar
// buttons are ~46x32 at 100% DPI).
const (
	captionButtonWidth  = 46
	captionButtonHeight = headerHeight
)

// declarative returns the CustomWidget declaration for this button, wiring up
// the paint callback and (after creation) the subclassed window procedure that
// tracks hover/press.
func (b *captionButton) declarative() CustomWidget {
	return CustomWidget{
		AssignTo:            &b.widget,
		MinSize:             Size{Width: captionButtonWidth, Height: captionButtonHeight},
		MaxSize:             Size{Width: captionButtonWidth, Height: captionButtonHeight},
		ClearsBackground:    true,
		InvalidatesOnResize: true,
		PaintMode:           PaintNormal,
		Paint:               b.paint,
		OnBoundsChanged:     b.subclassOnce,
	}
}

// subclassOnce installs our window procedure the first time the widget has a
// handle. OnBoundsChanged fires after creation, which is a safe hook point.
func (b *captionButton) subclassOnce() {
	if b.origProc != 0 || b.widget == nil {
		return
	}
	h := b.widget.Handle()
	b.origProc = win.GetWindowLongPtr(h, win.GWLP_WNDPROC)
	win.SetWindowLongPtr(h, win.GWLP_WNDPROC, syscall.NewCallback(b.wndProc))
}

func (b *captionButton) wndProc(hwnd win.HWND, msg uint32, wParam, lParam uintptr) uintptr {
	switch msg {
	case win.WM_MOUSEMOVE:
		if !b.hot {
			b.hot = true
			b.invalidate()
		}
		if !b.tracking {
			tme := win.TRACKMOUSEEVENT{
				CbSize:    uint32(unsafe.Sizeof(win.TRACKMOUSEEVENT{})),
				DwFlags:   win.TME_LEAVE,
				HwndTrack: hwnd,
			}
			b.tracking = win.TrackMouseEvent(&tme)
		}

	case win.WM_MOUSELEAVE:
		b.tracking = false
		if b.hot || b.pressed {
			b.hot = false
			b.pressed = false
			b.invalidate()
		}

	case win.WM_LBUTTONDOWN:
		b.pressed = true
		win.SetCapture(hwnd)
		b.invalidate()
		return 0

	case win.WM_LBUTTONUP:
		wasPressed := b.pressed
		b.pressed = false
		win.ReleaseCapture()
		b.invalidate()
		if wasPressed && b.onClick != nil {
			b.onClick()
		}
		return 0
	}
	return win.CallWindowProc(b.origProc, hwnd, msg, wParam, lParam)
}

func (b *captionButton) invalidate() {
	if b.widget != nil {
		b.widget.Invalidate()
		// Force an immediate repaint. After a drag-restore the normal paint queue
		// can be starved, leaving a stale maximize/restore glyph.
		win.UpdateWindow(b.widget.Handle())
	}
}

// paint draws the button: a flat background (dark, grey on hover, red for a
// hovered close) and a crisp white glyph — the modern dark-title-bar style used
// by apps like VS Code. We draw our own glyphs because the OS WINDOW theme
// paints a light button background that clashes with the dark header.
func (b *captionButton) paint(canvas *walk.Canvas, _ walk.Rectangle) error {
	// Use the widget's own client size (0,0-based). canvas.BoundsPixels() can
	// report a far larger region, which would push the glyph out of view.
	cb := b.widget.ClientBoundsPixels()

	// Background.
	bg := headerBG
	if b.hot || b.pressed {
		if b.kind == capClose {
			bg = walk.RGB(0xC4, 0x2B, 0x1C) // close-hover red
			if b.pressed {
				bg = walk.RGB(0xA8, 0x24, 0x17)
			}
		} else {
			bg = walk.RGB(0x33, 0x42, 0x52) // subtle slate hover
			if b.pressed {
				bg = walk.RGB(0x29, 0x36, 0x44)
			}
		}
	}
	local := walk.Rectangle{X: 0, Y: 0, Width: cb.Width, Height: cb.Height}
	if brush, err := walk.NewSolidColorBrush(bg); err == nil {
		_ = canvas.FillRectanglePixels(brush, local)
		brush.Dispose()
	}

	b.paintGlyph(canvas, local)
	return nil
}

// paintGlyph draws the crisp white min/max/restore/close mark, centred.
func (b *captionButton) paintGlyph(canvas *walk.Canvas, bounds walk.Rectangle) {
	dpi := canvas.DPI()
	brush, err := walk.NewSolidColorBrush(whiteText)
	if err != nil {
		return
	}
	defer brush.Dispose()
	pen, err := walk.NewGeometricPen(walk.PenSolid, 2*dpi/96, brush)
	if err != nil {
		return
	}
	defer pen.Dispose()

	// 10px glyph box, centred. The canvas paints in widget-local coordinates, so
	// the centre is width/2, height/2 (BoundsPixels().X/Y are parent-relative and
	// must NOT be added here).
	half := 5 * dpi / 96
	cx := bounds.Width / 2
	cy := bounds.Height / 2
	l, t, r, bot := cx-half, cy-half, cx+half, cy+half

	switch b.kind {
	case capMinimize:
		canvas.DrawLinePixels(pen, walk.Point{X: l, Y: cy}, walk.Point{X: r, Y: cy})

	case capMaxRestore:
		if b.zoomedFn != nil && b.zoomedFn() {
			// Restore: a back square peeking behind a front square.
			off := 3 * dpi / 96
			canvas.DrawRectanglePixels(pen, walk.Rectangle{X: l + off, Y: t - off, Width: (r - l) - off, Height: (bot - t) - off})
			canvas.DrawRectanglePixels(pen, walk.Rectangle{X: l, Y: t, Width: (r - l) - off, Height: (bot - t) - off})
		} else {
			canvas.DrawRectanglePixels(pen, walk.Rectangle{X: l, Y: t, Width: r - l, Height: bot - t})
		}

	case capClose:
		canvas.DrawLinePixels(pen, walk.Point{X: l, Y: t}, walk.Point{X: r, Y: bot})
		canvas.DrawLinePixels(pen, walk.Point{X: l, Y: bot}, walk.Point{X: r, Y: t})
	}
}
