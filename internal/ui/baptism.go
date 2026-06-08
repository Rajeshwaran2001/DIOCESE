//go:build windows

package ui

import (
	"strings"

	"diocese-certs/internal/model"
	"diocese-certs/internal/printing"

	"github.com/lxn/walk"
	. "github.com/lxn/walk/declarative"
)

// baptismSection owns the model.Baptism tab: entry form + history.
type baptismSection struct {
	app *App

	number                             *walk.LineEdit
	whenBaptized, saidToBeBorn         *walk.DateEdit
	christianName, surnameFormer       *walk.LineEdit
	sex                                *walk.ComboBox
	fatherName, motherName, trade      *walk.LineEdit
	godparents, whereBaptized          *walk.LineEdit
	signatureByWhom, baptizedByName    *walk.LineEdit
	witnessDate, preparedBy, checkedBy *walk.LineEdit

	editingID int64

	search *walk.LineEdit
	tv     *walk.TableView
	model  *stringTableModel
}

func newBaptismSection(app *App) *baptismSection {
	return &baptismSection{app: app, model: &stringTableModel{}}
}

func (s *baptismSection) Page() TabPage {
	return TabPage{
		Title:  "model.Baptism",
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

func (s *baptismSection) entryPage() TabPage {
	return TabPage{
		Title:  "New / Edit Entry",
		Layout: VBox{},
		Children: []Widget{
			Composite{
				Layout: Grid{Columns: 2, Spacing: 8},
				Children: []Widget{
					Label{Text: "Number:"},
					LineEdit{AssignTo: &s.number},

					Label{Text: "When Baptized:"},
					DateEdit{AssignTo: &s.whenBaptized},

					Label{Text: "Said to be Born:"},
					DateEdit{AssignTo: &s.saidToBeBorn},

					Label{Text: "Christian Name:"},
					LineEdit{AssignTo: &s.christianName},

					Label{Text: "Surname / Former Name:"},
					LineEdit{AssignTo: &s.surnameFormer},

					Label{Text: "Sex:"},
					ComboBox{
						AssignTo: &s.sex,
						Editable: true,
						Model:    []string{"Male", "Female"},
					},

					Label{Text: "Father Name:"},
					LineEdit{AssignTo: &s.fatherName},

					Label{Text: "Mother Name:"},
					LineEdit{AssignTo: &s.motherName},

					Label{Text: "Trade or Profession:"},
					LineEdit{AssignTo: &s.trade},

					Label{Text: "Names of God-Parents:"},
					LineEdit{AssignTo: &s.godparents},

					Label{Text: "Where Baptized:"},
					LineEdit{AssignTo: &s.whereBaptized},

					Label{Text: "Signature By Whom Baptized:"},
					LineEdit{AssignTo: &s.signatureByWhom},

					Label{Text: "Mr/Rev. (baptized by):"},
					LineEdit{AssignTo: &s.baptizedByName},

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

func (s *baptismSection) historyPage() TabPage {
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
					{Title: "Christian Name", Width: 200},
					{Title: "Surname", Width: 160},
					{Title: "When Baptized", Width: 120},
					{Title: "Father", Width: 160},
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

func (s *baptismSection) collect() *model.Baptism {
	t := strings.TrimSpace
	return &model.Baptism{
		ID:                      s.editingID,
		Number:                  t(s.number.Text()),
		WhenBaptized:            fmtDate(s.whenBaptized.Date()),
		SaidToBeBorn:            fmtDate(s.saidToBeBorn.Date()),
		ChristianName:           t(s.christianName.Text()),
		SurnameFormerName:       t(s.surnameFormer.Text()),
		Sex:                     t(s.sex.Text()),
		FatherName:              t(s.fatherName.Text()),
		MotherName:              t(s.motherName.Text()),
		TradeOrProfession:       t(s.trade.Text()),
		NamesOfGodparents:       t(s.godparents.Text()),
		WhereBaptized:           t(s.whereBaptized.Text()),
		SignatureByWhomBaptized: t(s.signatureByWhom.Text()),
		BaptizedByName:          t(s.baptizedByName.Text()),
		WitnessDate:             t(s.witnessDate.Text()),
		PreparedBy:              t(s.preparedBy.Text()),
		CheckedBy:               t(s.checkedBy.Text()),
	}
}

func (s *baptismSection) populate(b *model.Baptism) {
	s.editingID = b.ID
	s.number.SetText(b.Number)
	s.whenBaptized.SetDate(parseDate(b.WhenBaptized))
	s.saidToBeBorn.SetDate(parseDate(b.SaidToBeBorn))
	s.christianName.SetText(b.ChristianName)
	s.surnameFormer.SetText(b.SurnameFormerName)
	s.sex.SetText(b.Sex)
	s.fatherName.SetText(b.FatherName)
	s.motherName.SetText(b.MotherName)
	s.trade.SetText(b.TradeOrProfession)
	s.godparents.SetText(b.NamesOfGodparents)
	s.whereBaptized.SetText(b.WhereBaptized)
	s.signatureByWhom.SetText(b.SignatureByWhomBaptized)
	s.baptizedByName.SetText(b.BaptizedByName)
	s.witnessDate.SetText(b.WitnessDate)
	s.preparedBy.SetText(b.PreparedBy)
	s.checkedBy.SetText(b.CheckedBy)
}

func (s *baptismSection) clearForm() {
	s.editingID = 0
	s.sex.SetText("")
	for _, e := range []*walk.LineEdit{
		s.number, s.christianName, s.surnameFormer, s.fatherName, s.motherName,
		s.trade, s.godparents, s.whereBaptized, s.signatureByWhom, s.baptizedByName,
		s.witnessDate, s.preparedBy, s.checkedBy,
	} {
		e.SetText("")
	}
}

func (s *baptismSection) onSave(print bool) {
	if !s.app.requireDB() {
		return
	}
	b := s.collect()
	if b.ChristianName == "" {
		s.app.infoBox("Required field", "Please enter the Christian name before saving.")
		return
	}
	if err := s.app.db.SaveBaptism(b); err != nil {
		s.app.errorBox("Save failed", err)
		return
	}
	s.editingID = b.ID
	s.refresh()
	if print {
		if err := printing.PrintBaptism(s.app.cfg, b); err != nil {
			s.app.errorBox("Print failed", err)
			return
		}
	}
	s.app.infoBox("Saved", "model.Baptism certificate saved successfully.")
}

func (s *baptismSection) selectedID() (int64, bool) {
	i := s.tv.CurrentIndex()
	if i < 0 {
		s.app.infoBox("No selection", "Please select a row first.")
		return 0, false
	}
	return s.model.IDAt(i), true
}

func (s *baptismSection) onView() {
	id, ok := s.selectedID()
	if !ok || !s.app.requireDB() {
		return
	}
	b, err := s.app.db.GetBaptism(id)
	if err != nil {
		s.app.errorBox("Load failed", err)
		return
	}
	s.populate(b)
	s.app.infoBox("Loaded", "Record loaded into the New / Edit Entry tab.")
}

func (s *baptismSection) onReprint() {
	id, ok := s.selectedID()
	if !ok || !s.app.requireDB() {
		return
	}
	b, err := s.app.db.GetBaptism(id)
	if err != nil {
		s.app.errorBox("Load failed", err)
		return
	}
	if err := printing.PrintBaptism(s.app.cfg, b); err != nil {
		s.app.errorBox("Print failed", err)
	}
}

func (s *baptismSection) onDelete() {
	id, ok := s.selectedID()
	if !ok || !s.app.requireDB() {
		return
	}
	if !s.app.confirm("Confirm delete", "Delete this baptism certificate permanently?") {
		return
	}
	if err := s.app.db.DeleteBaptism(id); err != nil {
		s.app.errorBox("Delete failed", err)
		return
	}
	if s.editingID == id {
		s.clearForm()
	}
	s.refresh()
}

func (s *baptismSection) refresh() {
	if s.app.db == nil {
		s.model.SetRows(nil, nil)
		return
	}
	term := ""
	if s.search != nil {
		term = s.search.Text()
	}
	list, err := s.app.db.ListBaptisms(term)
	if err != nil {
		s.app.errorBox("Load failed", err)
		return
	}
	ids := make([]int64, 0, len(list))
	rows := make([][]string, 0, len(list))
	for _, b := range list {
		ids = append(ids, b.ID)
		rows = append(rows, []string{b.Number, b.ChristianName, b.SurnameFormerName, b.WhenBaptized, b.FatherName})
	}
	s.model.SetRows(ids, rows)
}
