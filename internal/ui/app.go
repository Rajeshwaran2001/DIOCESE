//go:build windows

// Package ui builds the native Win32 window, tabs and forms (lxn/walk) and
// wires them to the store, config and printing packages.
package ui

import (
	"fmt"
	"os"
	"time"

	"diocese-certs/internal/config"
	"diocese-certs/internal/store"

	"github.com/lxn/walk"
	. "github.com/lxn/walk/declarative"
)

const dateLayout = "2006-01-02"

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
}

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

	// Build the main window (Create, not Run, so we can initialise data first).
	if err := (MainWindow{
		AssignTo: &app.mw,
		Title:    "Diocese of Madurai Ramnad — Certificate Manager",
		MinSize:  Size{Width: 980, Height: 700},
		Size:     Size{Width: 1100, Height: 760},
		Layout:   VBox{},
		Children: []Widget{
			TabWidget{
				Pages: []TabPage{
					app.death.Page(),
					app.marriage.Page(),
					app.baptism.Page(),
					app.settings.Page(),
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

	// Initial data load into the history tables (db may be nil if path bad).
	app.refreshAll()

	app.mw.Run()
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
