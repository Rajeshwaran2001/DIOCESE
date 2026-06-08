//go:build windows

package ui

import (
	"strings"

	"diocese-certs/internal/model"
	"diocese-certs/internal/printing"

	"github.com/lxn/walk"
	. "github.com/lxn/walk/declarative"
)

// marriageSection owns the Marriage tab. The entry form shows Party A and
// Party B side by side (three-column grid: Label | Party A | Party B).
type marriageSection struct {
	app *App

	// shared / parent fields
	serialNo, number      *walk.LineEdit
	whenMarried           *walk.DateEdit
	placeSolemnized       *walk.LineEdit
	witnesses             *walk.LineEdit
	signatureOfLicensee   *walk.LineEdit
	registrar             *walk.LineEdit
	witnessDate           *walk.LineEdit
	preparedBy, checkedBy *walk.LineEdit

	// Party A widgets
	aName, aSurname, aAge, aCondition, aRank, aResidence, aFather, aSignature *walk.LineEdit
	// Party B widgets
	bName, bSurname, bAge, bCondition, bRank, bResidence, bFather, bSignature *walk.LineEdit

	editingID int64

	// history
	search *walk.LineEdit
	tv     *walk.TableView
	model  *stringTableModel
}

func newMarriageSection(app *App) *marriageSection {
	return &marriageSection{app: app, model: &stringTableModel{}}
}

func (s *marriageSection) Page() TabPage {
	return TabPage{
		Title:  "Marriage",
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

func (s *marriageSection) entryPage() TabPage {
	// Three-column grid: field label, Party A value, Party B value.
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
					Label{Text: "When Married:"},
					DateEdit{AssignTo: &s.whenMarried},
					Label{Text: "Place where Marriage was Solemnized:"},
					LineEdit{AssignTo: &s.placeSolemnized},
				},
			},
			GroupBox{
				Title:  "Contracting Parties",
				Layout: Grid{Columns: 3, Spacing: 8},
				Children: []Widget{
					Label{Text: ""}, Label{Text: "Party A (e.g. Groom)"}, Label{Text: "Party B (e.g. Bride)"},

					Label{Text: "Name of Party:"},
					LineEdit{AssignTo: &s.aName}, LineEdit{AssignTo: &s.bName},

					Label{Text: "Surname:"},
					LineEdit{AssignTo: &s.aSurname}, LineEdit{AssignTo: &s.bSurname},

					Label{Text: "Age:"},
					LineEdit{AssignTo: &s.aAge}, LineEdit{AssignTo: &s.bAge},

					Label{Text: "Condition:"},
					LineEdit{AssignTo: &s.aCondition}, LineEdit{AssignTo: &s.bCondition},

					Label{Text: "Rank or Profession:"},
					LineEdit{AssignTo: &s.aRank}, LineEdit{AssignTo: &s.bRank},

					Label{Text: "Residence at the time of Marriage:"},
					LineEdit{AssignTo: &s.aResidence}, LineEdit{AssignTo: &s.bResidence},

					Label{Text: "Father's Name:"},
					LineEdit{AssignTo: &s.aFather}, LineEdit{AssignTo: &s.bFather},

					Label{Text: "Signature of Contracting Party:"},
					LineEdit{AssignTo: &s.aSignature}, LineEdit{AssignTo: &s.bSignature},
				},
			},
			Composite{
				Layout: Grid{Columns: 2, Spacing: 8},
				Children: []Widget{
					Label{Text: "Witnesses:"},
					LineEdit{AssignTo: &s.witnesses},
					Label{Text: "Signature of the Licensee:"},
					LineEdit{AssignTo: &s.signatureOfLicensee},
					Label{Text: "Registrar Name:"},
					LineEdit{AssignTo: &s.registrar},
					Label{Text: "Witness (… day of … Two thousand and …):"},
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

func (s *marriageSection) historyPage() TabPage {
	return TabPage{
		Title:  "History",
		Layout: VBox{},
		Children: []Widget{
			Composite{
				Layout: HBox{},
				Children: []Widget{
					Label{Text: "Search:"},
					LineEdit{AssignTo: &s.search, OnTextChanged: s.refresh},
					PushButton{Text: "Refresh", OnClicked: s.refresh},
				},
			},
			TableView{
				AssignTo:         &s.tv,
				AlternatingRowBG: true,
				Model:            s.model,
				OnItemActivated:  s.onView,
				Columns: []TableViewColumn{
					{Title: "No.", Width: 60},
					{Title: "Party A", Width: 200},
					{Title: "Party B", Width: 200},
					{Title: "When Married", Width: 120},
				},
			},
			Composite{
				Layout: HBox{},
				Children: []Widget{
					PushButton{Text: "View", OnClicked: s.onView},
					PushButton{Text: "Edit", OnClicked: s.onView},
					PushButton{Text: "Reprint", OnClicked: s.onReprint},
					PushButton{Text: "Delete", OnClicked: s.onDelete},
					HSpacer{},
				},
			},
		},
	}
}

func (s *marriageSection) collect() *model.MarriageReturn {
	t := strings.TrimSpace
	return &model.MarriageReturn{
		ID:                  s.editingID,
		SerialNo:            t(s.serialNo.Text()),
		Number:              t(s.number.Text()),
		WhenMarried:         fmtDate(s.whenMarried.Date()),
		PlaceSolemnized:     t(s.placeSolemnized.Text()),
		Witnesses:           t(s.witnesses.Text()),
		SignatureOfLicensee: t(s.signatureOfLicensee.Text()),
		RegistrarName:       t(s.registrar.Text()),
		WitnessDate:         t(s.witnessDate.Text()),
		PreparedBy:          t(s.preparedBy.Text()),
		CheckedBy:           t(s.checkedBy.Text()),
		PartyA: model.MarriageParty{
			Side:                      "A",
			NameOfParty:               t(s.aName.Text()),
			Surname:                   t(s.aSurname.Text()),
			Age:                       t(s.aAge.Text()),
			Condition:                 t(s.aCondition.Text()),
			RankOrProfession:          t(s.aRank.Text()),
			ResidenceAtMarriage:       t(s.aResidence.Text()),
			FathersName:               t(s.aFather.Text()),
			SignatureContractingParty: t(s.aSignature.Text()),
		},
		PartyB: model.MarriageParty{
			Side:                      "B",
			NameOfParty:               t(s.bName.Text()),
			Surname:                   t(s.bSurname.Text()),
			Age:                       t(s.bAge.Text()),
			Condition:                 t(s.bCondition.Text()),
			RankOrProfession:          t(s.bRank.Text()),
			ResidenceAtMarriage:       t(s.bResidence.Text()),
			FathersName:               t(s.bFather.Text()),
			SignatureContractingParty: t(s.bSignature.Text()),
		},
	}
}

func (s *marriageSection) populate(m *model.MarriageReturn) {
	s.editingID = m.ID
	s.serialNo.SetText(m.SerialNo)
	s.number.SetText(m.Number)
	s.whenMarried.SetDate(parseDate(m.WhenMarried))
	s.placeSolemnized.SetText(m.PlaceSolemnized)
	s.witnesses.SetText(m.Witnesses)
	s.signatureOfLicensee.SetText(m.SignatureOfLicensee)
	s.registrar.SetText(m.RegistrarName)
	s.witnessDate.SetText(m.WitnessDate)
	s.preparedBy.SetText(m.PreparedBy)
	s.checkedBy.SetText(m.CheckedBy)

	a, b := m.PartyA, m.PartyB
	s.aName.SetText(a.NameOfParty)
	s.aSurname.SetText(a.Surname)
	s.aAge.SetText(a.Age)
	s.aCondition.SetText(a.Condition)
	s.aRank.SetText(a.RankOrProfession)
	s.aResidence.SetText(a.ResidenceAtMarriage)
	s.aFather.SetText(a.FathersName)
	s.aSignature.SetText(a.SignatureContractingParty)
	s.bName.SetText(b.NameOfParty)
	s.bSurname.SetText(b.Surname)
	s.bAge.SetText(b.Age)
	s.bCondition.SetText(b.Condition)
	s.bRank.SetText(b.RankOrProfession)
	s.bResidence.SetText(b.ResidenceAtMarriage)
	s.bFather.SetText(b.FathersName)
	s.bSignature.SetText(b.SignatureContractingParty)
}

func (s *marriageSection) clearForm() {
	s.editingID = 0
	for _, e := range []*walk.LineEdit{
		s.serialNo, s.number, s.placeSolemnized, s.witnesses, s.signatureOfLicensee,
		s.registrar, s.witnessDate, s.preparedBy, s.checkedBy,
		s.aName, s.aSurname, s.aAge, s.aCondition, s.aRank, s.aResidence, s.aFather, s.aSignature,
		s.bName, s.bSurname, s.bAge, s.bCondition, s.bRank, s.bResidence, s.bFather, s.bSignature,
	} {
		e.SetText("")
	}
}

func (s *marriageSection) onSave(print bool) {
	if !s.app.requireDB() {
		return
	}
	m := s.collect()
	if m.PartyA.NameOfParty == "" && m.PartyB.NameOfParty == "" {
		s.app.infoBox("Required field", "Please enter at least one party's name before saving.")
		return
	}
	if err := s.app.db.SaveMarriage(m); err != nil {
		s.app.errorBox("Save failed", err)
		return
	}
	s.editingID = m.ID
	s.refresh()
	if print {
		if err := printing.PrintMarriage(s.app.cfg, m); err != nil {
			s.app.errorBox("Print failed", err)
			return
		}
	}
	s.app.infoBox("Saved", "Marriage return saved successfully.")
}

func (s *marriageSection) selectedID() (int64, bool) {
	i := s.tv.CurrentIndex()
	if i < 0 {
		s.app.infoBox("No selection", "Please select a row first.")
		return 0, false
	}
	return s.model.IDAt(i), true
}

func (s *marriageSection) onView() {
	id, ok := s.selectedID()
	if !ok || !s.app.requireDB() {
		return
	}
	m, err := s.app.db.GetMarriage(id)
	if err != nil {
		s.app.errorBox("Load failed", err)
		return
	}
	s.populate(m)
	s.app.infoBox("Loaded", "Record loaded into the New / Edit Entry tab.")
}

func (s *marriageSection) onReprint() {
	id, ok := s.selectedID()
	if !ok || !s.app.requireDB() {
		return
	}
	m, err := s.app.db.GetMarriage(id)
	if err != nil {
		s.app.errorBox("Load failed", err)
		return
	}
	if err := printing.PrintMarriage(s.app.cfg, m); err != nil {
		s.app.errorBox("Print failed", err)
	}
}

func (s *marriageSection) onDelete() {
	id, ok := s.selectedID()
	if !ok || !s.app.requireDB() {
		return
	}
	if !s.app.confirm("Confirm delete", "Delete this marriage return permanently?") {
		return
	}
	if err := s.app.db.DeleteMarriage(id); err != nil {
		s.app.errorBox("Delete failed", err)
		return
	}
	if s.editingID == id {
		s.clearForm()
	}
	s.refresh()
}

func (s *marriageSection) refresh() {
	if s.app.db == nil {
		s.model.SetRows(nil, nil)
		return
	}
	term := ""
	if s.search != nil {
		term = s.search.Text()
	}
	list, err := s.app.db.ListMarriages(term)
	if err != nil {
		s.app.errorBox("Load failed", err)
		return
	}
	ids := make([]int64, 0, len(list))
	rows := make([][]string, 0, len(list))
	for _, m := range list {
		partyA := strings.TrimSpace(m.PartyA.NameOfParty + " " + m.PartyA.Surname)
		partyB := strings.TrimSpace(m.PartyB.NameOfParty + " " + m.PartyB.Surname)
		ids = append(ids, m.ID)
		rows = append(rows, []string{m.Number, partyA, partyB, m.WhenMarried})
	}
	s.model.SetRows(ids, rows)
}
