//go:build windows

package ui

import (
	"strings"

	"diocese-certs/internal/config"
	"diocese-certs/internal/printing"

	"github.com/lxn/walk"
	. "github.com/lxn/walk/declarative"
)

// settingsSection owns the Settings tab: data path, paper size, font, printer,
// and per-form print calibration with an alignment test.
type settingsSection struct {
	app *App

	dataPathEdit *walk.LineEdit
	paperSize    *walk.ComboBox
	printerName  *walk.LineEdit
	fontName     *walk.LineEdit
	fontSize     *walk.NumberEdit

	// calibration X/Y per form
	deathX, deathY       *walk.NumberEdit
	marriageX, marriageY *walk.NumberEdit
	baptismX, baptismY   *walk.NumberEdit
}

func newSettingsSection(app *App) *settingsSection {
	return &settingsSection{app: app}
}

func (s *settingsSection) Page() TabPage {
	return TabPage{
		Title:  "Settings",
		Layout: VBox{},
		Children: []Widget{
			GroupBox{
				Title:  "Data location",
				Layout: Grid{Columns: 3, Spacing: 8},
				Children: []Widget{
					Label{Text: "Database folder:"},
					LineEdit{AssignTo: &s.dataPathEdit, ReadOnly: true, Text: s.app.cfg.DataPath},
					PushButton{Text: "Change…", OnClicked: s.onChangeFolder},
					Label{Text: "Config file:"},
					Label{Text: s.app.cfg.ConfigFilePath(), ColumnSpan: 2},
				},
			},
			GroupBox{
				Title:  "Printing",
				Layout: Grid{Columns: 2, Spacing: 8},
				Children: []Widget{
					Label{Text: "Paper size:"},
					ComboBox{
						AssignTo: &s.paperSize,
						Model:    []string{"A4", "Letter"},
						Value:    s.app.cfg.PaperSize,
					},
					Label{Text: "Printer (blank = system default):"},
					LineEdit{AssignTo: &s.printerName, Text: s.app.cfg.PrinterName},
					Label{Text: "Font name:"},
					LineEdit{AssignTo: &s.fontName, Text: s.app.cfg.FontName},
					Label{Text: "Font size (pt):"},
					NumberEdit{AssignTo: &s.fontSize, Decimals: 0, MinValue: 6, MaxValue: 48, Value: float64(s.app.cfg.FontPointSize)},
				},
			},
			GroupBox{
				Title:  "Print calibration (millimetres — positive X = right, positive Y = down)",
				Layout: Grid{Columns: 4, Spacing: 8},
				Children: []Widget{
					Label{Text: "Form"}, Label{Text: "X offset (mm)"}, Label{Text: "Y offset (mm)"}, Label{Text: "Alignment test"},

					Label{Text: "Death Extract"},
					NumberEdit{AssignTo: &s.deathX, Decimals: 1, MinValue: -50, MaxValue: 50, Value: s.app.cfg.Calibration["death"].XmmOffset},
					NumberEdit{AssignTo: &s.deathY, Decimals: 1, MinValue: -50, MaxValue: 50, Value: s.app.cfg.Calibration["death"].YmmOffset},
					PushButton{Text: "Print test", OnClicked: func() { s.onAlignmentTest("death") }},

					Label{Text: "Marriage Return"},
					NumberEdit{AssignTo: &s.marriageX, Decimals: 1, MinValue: -50, MaxValue: 50, Value: s.app.cfg.Calibration["marriage"].XmmOffset},
					NumberEdit{AssignTo: &s.marriageY, Decimals: 1, MinValue: -50, MaxValue: 50, Value: s.app.cfg.Calibration["marriage"].YmmOffset},
					PushButton{Text: "Print test", OnClicked: func() { s.onAlignmentTest("marriage") }},

					Label{Text: "Baptism Certificate"},
					NumberEdit{AssignTo: &s.baptismX, Decimals: 1, MinValue: -50, MaxValue: 50, Value: s.app.cfg.Calibration["baptism"].XmmOffset},
					NumberEdit{AssignTo: &s.baptismY, Decimals: 1, MinValue: -50, MaxValue: 50, Value: s.app.cfg.Calibration["baptism"].YmmOffset},
					PushButton{Text: "Print test", OnClicked: func() { s.onAlignmentTest("baptism") }},
				},
			},
			Composite{
				Layout: HBox{},
				Children: []Widget{
					PushButton{Text: "Save Settings", OnClicked: s.onSave},
					HSpacer{},
				},
			},
			Label{
				Text: "Tip: print one alignment test on plain paper, lay it over a pre-printed form against\n" +
					"a window, and adjust the X/Y offsets until the values land on the printed lines.",
			},
			VSpacer{},
		},
	}
}

// collectInto reads the widgets back into the config (without saving).
func (s *settingsSection) collectInto() {
	c := s.app.cfg
	c.PaperSize = s.paperSize.Text()
	if c.PaperSize == "" {
		c.PaperSize = "A4"
	}
	c.PrinterName = strings.TrimSpace(s.printerName.Text())
	c.FontName = strings.TrimSpace(s.fontName.Text())
	if c.FontName == "" {
		c.FontName = "Times New Roman"
	}
	c.FontPointSize = int(s.fontSize.Value())
	if c.FontPointSize <= 0 {
		c.FontPointSize = 11
	}
	c.Calibration["death"] = config.CalibrationOffset{XmmOffset: s.deathX.Value(), YmmOffset: s.deathY.Value()}
	c.Calibration["marriage"] = config.CalibrationOffset{XmmOffset: s.marriageX.Value(), YmmOffset: s.marriageY.Value()}
	c.Calibration["baptism"] = config.CalibrationOffset{XmmOffset: s.baptismX.Value(), YmmOffset: s.baptismY.Value()}
}

func (s *settingsSection) onSave() {
	s.collectInto()
	if err := s.app.cfg.Save(); err != nil {
		s.app.errorBox("Save failed", err)
		return
	}
	s.app.infoBox("Saved", "Settings saved.")
}

func (s *settingsSection) onChangeFolder() {
	dlg := walk.FileDialog{
		Title:    "Choose database folder (USB drive or shared network folder)",
		FilePath: s.app.cfg.DataPath,
	}
	ok, err := dlg.ShowBrowseFolder(s.app.mw)
	if err != nil {
		s.app.errorBox("Folder picker failed", err)
		return
	}
	if !ok || dlg.FilePath == "" {
		return
	}
	newPath := dlg.FilePath
	// Point the app at the new folder and (re)open the DB there.
	old := s.app.cfg.DataPath
	s.app.cfg.DataPath = newPath
	if err := s.app.openDB(); err != nil {
		s.app.cfg.DataPath = old // revert on failure
		s.app.errorBox("Could not open database in that folder", err)
		return
	}
	if err := s.app.cfg.Save(); err != nil {
		s.app.errorBox("Could not save config", err)
		return
	}
	s.dataPathEdit.SetText(newPath)
	s.app.refreshAll()
	s.app.infoBox("Data folder changed",
		"The database now lives in:\n"+s.app.cfg.DBPath()+
			"\n\nNote: this points to a (new or existing) database in that folder; it does "+
			"not copy your old data. Copy diocese.db manually if you want to bring it along.")
}

func (s *settingsSection) onAlignmentTest(formID string) {
	// Apply current (possibly unsaved) calibration so the test reflects what
	// the clerk is tuning right now.
	s.collectInto()
	if err := printing.PrintAlignmentTest(s.app.cfg, formID); err != nil {
		s.app.errorBox("Alignment test failed", err)
		return
	}
}
