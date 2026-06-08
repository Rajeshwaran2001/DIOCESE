package printing

import "diocese-certs/internal/model"

// ----------------------------------------------------------------------------
// FORM LAYOUTS — coordinate overlay positions, in MILLIMETRES from the
// top-left corner of the printed page (portrait A4 = 210 x 297 mm).
//
// HOW TO READ THIS FILE
// ---------------------
// Each printable value has an (X, Y) position in millimetres. X is the distance
// from the LEFT edge to where the value's text begins. Y is the distance from
// the TOP edge to the text baseline-ish top. These were estimated by eye from
// photographs of the real pre-printed forms, so they are a STARTING POINT.
//
// Final tuning is done by the clerk in Settings -> Print Calibration, which
// applies a single global X/Y nudge (in mm) on top of every coordinate for that
// form. So you usually only need these to be "close" — the calibration test
// print and the X/Y offset get you the rest of the way. If one specific field
// is off on its own, edit just that line here and rebuild.
//
// Tip: 1 mm ~ 2.83 typographic points. A4 width 210 mm, height 297 mm.
// ----------------------------------------------------------------------------

// Point is a position in millimetres from the page's top-left corner.
type Point struct {
	Xmm float64
	Ymm float64
}

// TextItem is one piece of text to stamp on the page at a position (already in
// millimetres, before calibration offset is applied by the print engine).
type TextItem struct {
	Text string
	Xmm  float64
	Ymm  float64
}

// ============================================================================
// FORM 1 — DEATH EXTRACT (portrait)
// Labels are pre-printed on the left with a colon; we print only the value,
// starting just to the right of the colon column (~92 mm in).
// ============================================================================

// Column where most death-extract values begin (just right of the colons).
const deathValueX = 92.0

var deathLayout = map[string]Point{
	// label row positions (Y) down the page; X is the value column.
	"serial_no":              {150.0, 46.0}, // S.No. value, top-right of the form
	"number":                 {deathValueX, 51.0},
	"date_of_death":          {deathValueX, 62.0},
	"date_of_burial":         {deathValueX, 71.0},
	"name_of_dead_person":    {deathValueX, 81.0},
	"age":                    {deathValueX, 91.0},
	"occupation":             {deathValueX, 100.0},
	"cause_of_death":         {deathValueX, 109.0},
	"family_relation":        {deathValueX, 119.0},
	"place_of_death":         {deathValueX, 128.0},
	"person_who_buried_body": {deathValueX, 138.0},
	"place_of_burial":        {deathValueX, 147.0},

	// Certificate paragraph blanks (free-flowing text on the printed lines).
	"registrar_name": {30.0, 176.0}, // "I, ____ Diocesan Registrar"
	"pastorate_name": {98.0, 196.0}, // "...Register of death and burial of ____ pastorate"
	"witness_date":   {58.0, 233.0}, // "Witness my hand ____ day of ____"
	"prepared_by":    {34.0, 257.0}, // "Prepared by : ____"
	"checked_by":     {32.0, 283.0}, // "Checked by : ____"
}

// buildDeathItems maps a model.DeathExtract record onto its print positions.
func buildDeathItems(d *model.DeathExtract) []TextItem {
	pairs := []struct {
		key string
		val string
	}{
		{"serial_no", d.SerialNo},
		{"number", d.Number},
		{"date_of_death", d.DateOfDeath},
		{"date_of_burial", d.DateOfBurial},
		{"name_of_dead_person", d.NameOfDeadPerson},
		{"age", d.Age},
		{"occupation", d.Occupation},
		{"cause_of_death", d.CauseOfDeath},
		{"family_relation", d.FamilyRelation},
		{"place_of_death", d.PlaceOfDeath},
		{"person_who_buried_body", d.PersonWhoBuriedBody},
		{"place_of_burial", d.PlaceOfBurial},
		{"registrar_name", d.RegistrarName},
		{"pastorate_name", d.PastorateName},
		{"witness_date", d.WitnessDate},
		{"prepared_by", d.PreparedBy},
		{"checked_by", d.CheckedBy},
	}
	return itemsFrom(deathLayout, pairs)
}

// ============================================================================
// FORM 2 — MARRIAGE RETURNS COPY (portrait, two value columns)
// Each labelled row can hold a value for Party A and Party B side by side.
// ============================================================================

// X columns for the two parties. Single-value rows use the Party-A column.
const (
	marriagePartyAX = 95.0
	marriagePartyBX = 150.0
)

// Y position for each labelled row (shared by both party columns).
var marriageRowY = map[string]float64{
	"number":             50.0,
	"when_married":       60.0,
	"name_of_party":      70.0,
	"surname":            80.0,
	"age":                90.0,
	"condition":          100.0,
	"rank_or_profession": 110.0,
	"residence":          120.0,
	"fathers_name":       130.0,
	"signature_party":    140.0,
	"signature_licensee": 150.0,
	"witnesses":          160.0,
	"place_solemnized":   170.0,
}

// Single-value (non-party) marriage fields and the certificate blanks.
var marriageSingle = map[string]Point{
	"serial_no":      {150.0, 44.0}, // S.No. top-right
	"registrar_name": {30.0, 205.0},
	"witness_date":   {55.0, 224.0}, // "Witness my hand the ___ day of ___ Two thousand and ___"
	"prepared_by":    {34.0, 243.0},
	"checked_by":     {32.0, 252.0},
}

func buildMarriageItems(m *model.MarriageReturn) []TextItem {
	var items []TextItem

	// Per-party fields (two columns).
	addParty := func(p model.MarriageParty, x float64) {
		put := func(rowKey, val string) {
			if val == "" {
				return
			}
			items = append(items, TextItem{val, x, marriageRowY[rowKey]})
		}
		put("name_of_party", p.NameOfParty)
		put("surname", p.Surname)
		put("age", p.Age)
		put("condition", p.Condition)
		put("rank_or_profession", p.RankOrProfession)
		put("residence", p.ResidenceAtMarriage)
		put("fathers_name", p.FathersName)
		put("signature_party", p.SignatureContractingParty)
	}
	addParty(m.PartyA, marriagePartyAX)
	addParty(m.PartyB, marriagePartyBX)

	// Shared row fields (span both columns, anchored at Party-A column).
	if m.Number != "" {
		items = append(items, TextItem{m.Number, marriagePartyAX, marriageRowY["number"]})
	}
	if m.WhenMarried != "" {
		items = append(items, TextItem{m.WhenMarried, marriagePartyAX, marriageRowY["when_married"]})
	}
	if m.SignatureOfLicensee != "" {
		items = append(items, TextItem{m.SignatureOfLicensee, marriagePartyAX, marriageRowY["signature_licensee"]})
	}
	if m.Witnesses != "" {
		items = append(items, TextItem{m.Witnesses, marriagePartyAX, marriageRowY["witnesses"]})
	}
	if m.PlaceSolemnized != "" {
		items = append(items, TextItem{m.PlaceSolemnized, marriagePartyAX, marriageRowY["place_solemnized"]})
	}

	// Single fields + certificate blanks.
	single := []struct {
		key string
		val string
	}{
		{"serial_no", m.SerialNo},
		{"registrar_name", m.RegistrarName},
		{"witness_date", m.WitnessDate},
		{"prepared_by", m.PreparedBy},
		{"checked_by", m.CheckedBy},
	}
	items = append(items, itemsFrom(marriageSingle, single)...)
	return items
}

// ============================================================================
// FORM 3 — BAPTISM CERTIFICATE (portrait)
// Single column of values to the right of the pre-printed colons (~85 mm in).
// ============================================================================

const baptismValueX = 85.0

var baptismLayout = map[string]Point{
	"number":                     {baptismValueX, 40.0},
	"when_baptized":              {baptismValueX, 50.0},
	"said_to_be_born":            {baptismValueX, 60.0},
	"christian_name":             {baptismValueX, 70.0},
	"surname_former_name":        {baptismValueX, 80.0},
	"sex":                        {baptismValueX, 90.0},
	"father_name":                {baptismValueX, 100.0},
	"mother_name":                {baptismValueX, 110.0},
	"trade_or_profession":        {baptismValueX, 120.0},
	"names_of_godparents":        {baptismValueX, 130.0},
	"where_baptized":             {baptismValueX, 140.0},
	"signature_by_whom_baptized": {baptismValueX, 150.0},

	// Certificate paragraph blanks.
	"baptized_by_name": {40.0, 178.0}, // "Mr/Rev. ____ Diocesan Registrar"
	"witness_date":     {55.0, 210.0}, // "Witness my hand the ___ day of ___ Two thousand and ___"
	"prepared_by":      {34.0, 235.0},
	"checked_by":       {32.0, 250.0},
}

func buildBaptismItems(b *model.Baptism) []TextItem {
	pairs := []struct {
		key string
		val string
	}{
		{"number", b.Number},
		{"when_baptized", b.WhenBaptized},
		{"said_to_be_born", b.SaidToBeBorn},
		{"christian_name", b.ChristianName},
		{"surname_former_name", b.SurnameFormerName},
		{"sex", b.Sex},
		{"father_name", b.FatherName},
		{"mother_name", b.MotherName},
		{"trade_or_profession", b.TradeOrProfession},
		{"names_of_godparents", b.NamesOfGodparents},
		{"where_baptized", b.WhereBaptized},
		{"signature_by_whom_baptized", b.SignatureByWhomBaptized},
		{"baptized_by_name", b.BaptizedByName},
		{"witness_date", b.WitnessDate},
		{"prepared_by", b.PreparedBy},
		{"checked_by", b.CheckedBy},
	}
	return itemsFrom(baptismLayout, pairs)
}

// itemsFrom turns (key,value) pairs into TextItems using a position map,
// skipping blank values and keys without a defined position.
func itemsFrom(layout map[string]Point, pairs []struct{ key, val string }) []TextItem {
	var items []TextItem
	for _, p := range pairs {
		if p.val == "" {
			continue
		}
		pos, ok := layout[p.key]
		if !ok {
			continue
		}
		items = append(items, TextItem{p.val, pos.Xmm, pos.Ymm})
	}
	return items
}
