//go:build windows

package ui

import (
	"strings"

	"diocese-certs/internal/model"
	"diocese-certs/internal/printing"

	"github.com/lxn/walk"
	. "github.com/lxn/walk/declarative"
)

// deathSection owns the Death tab: an entry form and a history table.
type deathSection struct {
	app *App

	// entry widgets
	serialNo, number            *walk.LineEdit
	dateOfDeath, dateOfBurial   *walk.DateEdit
	name, age, occupation       *walk.LineEdit
	cause, family, placeOfDeath *walk.LineEdit
	buriedBy, placeOfBurial     *walk.LineEdit
	registrar, pastorate        *walk.LineEdit
	witnessDate                 *walk.LineEdit
	preparedBy, checkedBy       *walk.LineEdit

	editingID int64 // 0 = new record

	// history widgets
	search *walk.LineEdit
	tv     *walk.TableView
	model  *stringTableModel
}

func newDeathSection(app *App) *deathSection {
	return &deathSection{app: app, model: &stringTableModel{}}
}

func (s *deathSection) Page() TabPage {
	return TabPage{
		Title:  "Death",
		Layout: VBox{},
		Children: []Widget{
			TabWidget{
				Pages: []TabPage{
					s.entryPage(),
					s.historyPage(),
				},
			},
		},
	}
}

func (s *deathSection) entryPage() TabPage {
	return TabPage{
		Title:  "New / Edit Entry",
		Layout: VBox{},
		Children: []Widget{
			Composite{
				Layout: Grid{Columns: 2, Spacing: 8},
				Children: []Widget{
					Label{Text: "S.No.:"},
					LineEdit{AssignTo: &s.serialNo},

					Label{Text: "Number:"},
					LineEdit{AssignTo: &s.number},

					Label{Text: "Date of Death:"},
					DateEdit{AssignTo: &s.dateOfDeath},

					Label{Text: "Date of Burial:"},
					DateEdit{AssignTo: &s.dateOfBurial},

					Label{Text: "Name of Dead Person:"},
					LineEdit{AssignTo: &s.name},

					Label{Text: "Age:"},
					LineEdit{AssignTo: &s.age},

					Label{Text: "Occupation:"},
					LineEdit{AssignTo: &s.occupation},

					Label{Text: "Cause of Death:"},
					LineEdit{AssignTo: &s.cause},

					Label{Text: "Family Relation:"},
					LineEdit{AssignTo: &s.family},

					Label{Text: "Place of Death:"},
					LineEdit{AssignTo: &s.placeOfDeath},

					Label{Text: "Person Who Buried the Body:"},
					LineEdit{AssignTo: &s.buriedBy},

					Label{Text: "Place of Burial:"},
					LineEdit{AssignTo: &s.placeOfBurial},

					Label{Text: "Registrar Name:"},
					LineEdit{AssignTo: &s.registrar},

					Label{Text: "Pastorate Name:"},
					LineEdit{AssignTo: &s.pastorate},

					Label{Text: "Witness (… day of …):"},
					LineEdit{AssignTo: &s.witnessDate},

					Label{Text: "Prepared By:"},
					LineEdit{AssignTo: &s.preparedBy},

					Label{Text: "Checked By:"},
					LineEdit{AssignTo: &s.checkedBy},
				},
			},
			Composite{
				Layout: HBox{},
				Children: []Widget{
					PushButton{Text: "Save", OnClicked: func() { s.onSave(false) }},
					PushButton{Text: "Save && Print", OnClicked: func() { s.onSave(true) }},
					PushButton{Text: "Clear", OnClicked: s.clearForm},
					HSpacer{},
				},
			},
		},
	}
}

func (s *deathSection) historyPage() TabPage {
	return TabPage{
		Title:  "History",
		Layout: VBox{},
		Children: []Widget{
			Composite{
				Layout: HBox{},
				Children: []Widget{
					Label{Text: "Search:"},
					LineEdit{
						AssignTo:      &s.search,
						OnTextChanged: s.refresh,
					},
					PushButton{Text: "Refresh", OnClicked: s.refresh},
				},
			},
			TableView{
				AssignTo:         &s.tv,
				AlternatingRowBG: true,
				ColumnsOrderable: true,
				Model:            s.model,
				OnItemActivated:  s.onView, // double-click
				Columns: []TableViewColumn{
					{Title: "No.", Width: 60},
					{Title: "Name", Width: 220},
					{Title: "Date of Death", Width: 110},
					{Title: "Place of Death", Width: 180},
					{Title: "Age", Width: 60},
				},
			},
			Composite{
				Layout: HBox{},
				Children: []Widget{
					PushButton{Text: "View", OnClicked: s.onView},
					PushButton{Text: "Edit", OnClicked: s.onEdit},
					PushButton{Text: "Reprint", OnClicked: s.onReprint},
					PushButton{Text: "Delete", OnClicked: s.onDelete},
					HSpacer{},
				},
			},
		},
	}
}

// ----------------------------------------------------------------------------
// Form <-> record
// ----------------------------------------------------------------------------

func (s *deathSection) collect() *model.DeathExtract {
	return &model.DeathExtract{
		ID:                  s.editingID,
		SerialNo:            strings.TrimSpace(s.serialNo.Text()),
		Number:              strings.TrimSpace(s.number.Text()),
		DateOfDeath:         fmtDate(s.dateOfDeath.Date()),
		DateOfBurial:        fmtDate(s.dateOfBurial.Date()),
		NameOfDeadPerson:    strings.TrimSpace(s.name.Text()),
		Age:                 strings.TrimSpace(s.age.Text()),
		Occupation:          strings.TrimSpace(s.occupation.Text()),
		CauseOfDeath:        strings.TrimSpace(s.cause.Text()),
		FamilyRelation:      strings.TrimSpace(s.family.Text()),
		PlaceOfDeath:        strings.TrimSpace(s.placeOfDeath.Text()),
		PersonWhoBuriedBody: strings.TrimSpace(s.buriedBy.Text()),
		PlaceOfBurial:       strings.TrimSpace(s.placeOfBurial.Text()),
		RegistrarName:       strings.TrimSpace(s.registrar.Text()),
		PastorateName:       strings.TrimSpace(s.pastorate.Text()),
		WitnessDate:         strings.TrimSpace(s.witnessDate.Text()),
		PreparedBy:          strings.TrimSpace(s.preparedBy.Text()),
		CheckedBy:           strings.TrimSpace(s.checkedBy.Text()),
	}
}

func (s *deathSection) populate(d *model.DeathExtract) {
	s.editingID = d.ID
	s.serialNo.SetText(d.SerialNo)
	s.number.SetText(d.Number)
	s.dateOfDeath.SetDate(parseDate(d.DateOfDeath))
	s.dateOfBurial.SetDate(parseDate(d.DateOfBurial))
	s.name.SetText(d.NameOfDeadPerson)
	s.age.SetText(d.Age)
	s.occupation.SetText(d.Occupation)
	s.cause.SetText(d.CauseOfDeath)
	s.family.SetText(d.FamilyRelation)
	s.placeOfDeath.SetText(d.PlaceOfDeath)
	s.buriedBy.SetText(d.PersonWhoBuriedBody)
	s.placeOfBurial.SetText(d.PlaceOfBurial)
	s.registrar.SetText(d.RegistrarName)
	s.pastorate.SetText(d.PastorateName)
	s.witnessDate.SetText(d.WitnessDate)
	s.preparedBy.SetText(d.PreparedBy)
	s.checkedBy.SetText(d.CheckedBy)
}

func (s *deathSection) clearForm() {
	s.editingID = 0
	for _, e := range []*walk.LineEdit{s.serialNo, s.number, s.name, s.age, s.occupation,
		s.cause, s.family, s.placeOfDeath, s.buriedBy, s.placeOfBurial, s.registrar,
		s.pastorate, s.witnessDate, s.preparedBy, s.checkedBy} {
		e.SetText("")
	}
}

// ----------------------------------------------------------------------------
// Actions
// ----------------------------------------------------------------------------

func (s *deathSection) onSave(print bool) {
	if !s.app.requireDB() {
		return
	}
	d := s.collect()
	if d.NameOfDeadPerson == "" {
		s.app.infoBox("Required field", "Please enter the name of the dead person before saving.")
		return
	}
	if err := s.app.db.SaveDeath(d); err != nil {
		s.app.errorBox("Save failed", err)
		return
	}
	s.editingID = d.ID
	s.refresh()
	if print {
		if err := printing.PrintDeath(s.app.cfg, d); err != nil {
			s.app.errorBox("Print failed", err)
			return
		}
	}
	s.app.infoBox("Saved", "Death extract saved successfully.")
}

// selectedID returns the record ID for the currently selected history row.
func (s *deathSection) selectedID() (int64, bool) {
	i := s.tv.CurrentIndex()
	if i < 0 {
		s.app.infoBox("No selection", "Please select a row first.")
		return 0, false
	}
	return s.model.IDAt(i), true
}

func (s *deathSection) onView() {
	id, ok := s.selectedID()
	if !ok || !s.app.requireDB() {
		return
	}
	d, err := s.app.db.GetDeath(id)
	if err != nil {
		s.app.errorBox("Load failed", err)
		return
	}
	s.populate(d)
	s.app.infoBox("Loaded", "Record loaded into the New / Edit Entry tab.")
}

func (s *deathSection) onEdit() { s.onView() }

func (s *deathSection) onReprint() {
	id, ok := s.selectedID()
	if !ok || !s.app.requireDB() {
		return
	}
	d, err := s.app.db.GetDeath(id)
	if err != nil {
		s.app.errorBox("Load failed", err)
		return
	}
	if err := printing.PrintDeath(s.app.cfg, d); err != nil {
		s.app.errorBox("Print failed", err)
	}
}

func (s *deathSection) onDelete() {
	id, ok := s.selectedID()
	if !ok || !s.app.requireDB() {
		return
	}
	if !s.app.confirm("Confirm delete", "Delete this death extract permanently?") {
		return
	}
	if err := s.app.db.DeleteDeath(id); err != nil {
		s.app.errorBox("Delete failed", err)
		return
	}
	if s.editingID == id {
		s.clearForm()
	}
	s.refresh()
}

func (s *deathSection) refresh() {
	if s.app.db == nil {
		s.model.SetRows(nil, nil)
		return
	}
	term := ""
	if s.search != nil {
		term = s.search.Text()
	}
	list, err := s.app.db.ListDeaths(term)
	if err != nil {
		s.app.errorBox("Load failed", err)
		return
	}
	ids := make([]int64, 0, len(list))
	rows := make([][]string, 0, len(list))
	for _, d := range list {
		ids = append(ids, d.ID)
		rows = append(rows, []string{d.Number, d.NameOfDeadPerson, d.DateOfDeath, d.PlaceOfDeath, d.Age})
	}
	s.model.SetRows(ids, rows)
}
