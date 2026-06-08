// Package model holds the plain data structures for the three record types.
// These are shared by the store (persistence), printing, and ui packages and
// have no dependencies of their own.
package model

// DeathExtract mirrors the death_extract table / Form 1.
type DeathExtract struct {
	ID                  int64
	SerialNo            string
	Number              string
	DateOfDeath         string
	DateOfBurial        string
	NameOfDeadPerson    string
	Age                 string
	Occupation          string
	CauseOfDeath        string
	FamilyRelation      string
	PlaceOfDeath        string
	PersonWhoBuriedBody string
	PlaceOfBurial       string
	RegistrarName       string
	PastorateName       string
	WitnessDate         string
	PreparedBy          string
	CheckedBy           string
	CreatedAt           string
	UpdatedAt           string
}

// MarriageParty is one side (groom or bride) of a marriage record.
type MarriageParty struct {
	ID                        int64
	MarriageID                int64
	Side                      string // "A" or "B"
	NameOfParty               string
	Surname                   string
	Age                       string
	Condition                 string
	RankOrProfession          string
	ResidenceAtMarriage       string
	FathersName               string
	SignatureContractingParty string
}

// MarriageReturn mirrors marriage_return / Form 2, with two parties attached.
type MarriageReturn struct {
	ID                  int64
	SerialNo            string
	Number              string
	WhenMarried         string
	PlaceSolemnized     string
	Witnesses           string
	SignatureOfLicensee string
	WitnessDate         string
	PreparedBy          string
	CheckedBy           string
	RegistrarName       string
	CreatedAt           string
	UpdatedAt           string
	PartyA              MarriageParty
	PartyB              MarriageParty
}

// Baptism mirrors baptism / Form 3.
type Baptism struct {
	ID                      int64
	Number                  string
	WhenBaptized            string
	SaidToBeBorn            string
	ChristianName           string
	SurnameFormerName       string
	Sex                     string
	FatherName              string
	MotherName              string
	TradeOrProfession       string
	NamesOfGodparents       string
	WhereBaptized           string
	SignatureByWhomBaptized string
	BaptizedByName          string
	WitnessDate             string
	PreparedBy              string
	CheckedBy               string
	CreatedAt               string
	UpdatedAt               string
}
