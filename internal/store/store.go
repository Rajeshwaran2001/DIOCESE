package store

import (
	"database/sql"
	"fmt"
	"strings"
	"time"

	"diocese-certs/internal/model"

	_ "modernc.org/sqlite"
)

// schemaVersion lets future builds run migrations safely.
const schemaVersion = 1

// ----------------------------------------------------------------------------
// DB wrapper
// ----------------------------------------------------------------------------

type DB struct {
	conn *sql.DB
}

// OpenDB opens (or creates) the SQLite database at path and runs migrations.
func OpenDB(path string) (*DB, error) {
	// _pragma busy_timeout helps when the DB lives on a shared network folder
	// and another clerk briefly holds a lock.
	dsn := fmt.Sprintf("file:%s?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)&_pragma=foreign_keys(ON)", path)
	conn, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	conn.SetMaxOpenConns(1) // SQLite + safety on flaky network shares
	if err := conn.Ping(); err != nil {
		conn.Close()
		return nil, err
	}
	db := &DB{conn: conn}
	if err := db.migrate(); err != nil {
		conn.Close()
		return nil, err
	}
	return db, nil
}

func (db *DB) Close() error {
	if db == nil || db.conn == nil {
		return nil
	}
	return db.conn.Close()
}

func nowStr() string { return time.Now().Format("2006-01-02 15:04:05") }

func (db *DB) migrate() error {
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS schema_info (version INTEGER NOT NULL)`,

		`CREATE TABLE IF NOT EXISTS death_extract (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			serial_no TEXT, number TEXT,
			date_of_death TEXT, date_of_burial TEXT,
			name_of_dead_person TEXT, age TEXT, occupation TEXT,
			cause_of_death TEXT, family_relation TEXT, place_of_death TEXT,
			person_who_buried_body TEXT, place_of_burial TEXT,
			registrar_name TEXT, pastorate_name TEXT, witness_date TEXT,
			prepared_by TEXT, checked_by TEXT,
			created_at TEXT, updated_at TEXT
		)`,

		`CREATE TABLE IF NOT EXISTS marriage_return (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			serial_no TEXT, number TEXT,
			when_married TEXT, place_solemnized TEXT,
			witnesses TEXT, signature_of_licensee TEXT,
			witness_date TEXT, prepared_by TEXT, checked_by TEXT,
			registrar_name TEXT,
			created_at TEXT, updated_at TEXT
		)`,

		`CREATE TABLE IF NOT EXISTS marriage_party (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			marriage_id INTEGER NOT NULL,
			side TEXT NOT NULL,
			name_of_party TEXT, surname TEXT, age TEXT, condition TEXT,
			rank_or_profession TEXT, residence_at_marriage TEXT,
			fathers_name TEXT, signature_contracting_party TEXT,
			FOREIGN KEY (marriage_id) REFERENCES marriage_return(id) ON DELETE CASCADE
		)`,

		`CREATE TABLE IF NOT EXISTS baptism (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			number TEXT, when_baptized TEXT, said_to_be_born TEXT,
			christian_name TEXT, surname_former_name TEXT, sex TEXT,
			father_name TEXT, mother_name TEXT, trade_or_profession TEXT,
			names_of_godparents TEXT, where_baptized TEXT,
			signature_by_whom_baptized TEXT, baptized_by_name TEXT,
			witness_date TEXT, prepared_by TEXT, checked_by TEXT,
			created_at TEXT, updated_at TEXT
		)`,

		`CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)`,
	}
	tx, err := db.conn.Begin()
	if err != nil {
		return err
	}
	for _, s := range stmts {
		if _, err := tx.Exec(s); err != nil {
			tx.Rollback()
			return fmt.Errorf("migrate: %w", err)
		}
	}
	// Record schema version once.
	var n int
	_ = tx.QueryRow(`SELECT COUNT(*) FROM schema_info`).Scan(&n)
	if n == 0 {
		if _, err := tx.Exec(`INSERT INTO schema_info(version) VALUES(?)`, schemaVersion); err != nil {
			tx.Rollback()
			return err
		}
	}
	return tx.Commit()
}

// ----------------------------------------------------------------------------
// Death extract CRUD
// ----------------------------------------------------------------------------

func (db *DB) SaveDeath(d *model.DeathExtract) error {
	now := nowStr()
	if d.ID == 0 {
		d.CreatedAt = now
		d.UpdatedAt = now
		res, err := db.conn.Exec(`INSERT INTO death_extract (
			serial_no, number, date_of_death, date_of_burial, name_of_dead_person,
			age, occupation, cause_of_death, family_relation, place_of_death,
			person_who_buried_body, place_of_burial, registrar_name, pastorate_name,
			witness_date, prepared_by, checked_by, created_at, updated_at)
			VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
			d.SerialNo, d.Number, d.DateOfDeath, d.DateOfBurial, d.NameOfDeadPerson,
			d.Age, d.Occupation, d.CauseOfDeath, d.FamilyRelation, d.PlaceOfDeath,
			d.PersonWhoBuriedBody, d.PlaceOfBurial, d.RegistrarName, d.PastorateName,
			d.WitnessDate, d.PreparedBy, d.CheckedBy, d.CreatedAt, d.UpdatedAt)
		if err != nil {
			return err
		}
		d.ID, _ = res.LastInsertId()
		return nil
	}
	d.UpdatedAt = now
	_, err := db.conn.Exec(`UPDATE death_extract SET
		serial_no=?, number=?, date_of_death=?, date_of_burial=?, name_of_dead_person=?,
		age=?, occupation=?, cause_of_death=?, family_relation=?, place_of_death=?,
		person_who_buried_body=?, place_of_burial=?, registrar_name=?, pastorate_name=?,
		witness_date=?, prepared_by=?, checked_by=?, updated_at=? WHERE id=?`,
		d.SerialNo, d.Number, d.DateOfDeath, d.DateOfBurial, d.NameOfDeadPerson,
		d.Age, d.Occupation, d.CauseOfDeath, d.FamilyRelation, d.PlaceOfDeath,
		d.PersonWhoBuriedBody, d.PlaceOfBurial, d.RegistrarName, d.PastorateName,
		d.WitnessDate, d.PreparedBy, d.CheckedBy, d.UpdatedAt, d.ID)
	return err
}

func scanDeath(rows *sql.Rows) (*model.DeathExtract, error) {
	d := &model.DeathExtract{}
	err := rows.Scan(&d.ID, &d.SerialNo, &d.Number, &d.DateOfDeath, &d.DateOfBurial,
		&d.NameOfDeadPerson, &d.Age, &d.Occupation, &d.CauseOfDeath, &d.FamilyRelation,
		&d.PlaceOfDeath, &d.PersonWhoBuriedBody, &d.PlaceOfBurial, &d.RegistrarName,
		&d.PastorateName, &d.WitnessDate, &d.PreparedBy, &d.CheckedBy, &d.CreatedAt, &d.UpdatedAt)
	return d, err
}

const deathCols = `id, serial_no, number, date_of_death, date_of_burial, name_of_dead_person,
	age, occupation, cause_of_death, family_relation, place_of_death,
	person_who_buried_body, place_of_burial, registrar_name, pastorate_name,
	witness_date, prepared_by, checked_by, created_at, updated_at`

func (db *DB) GetDeath(id int64) (*model.DeathExtract, error) {
	rows, err := db.conn.Query(`SELECT `+deathCols+` FROM death_extract WHERE id=?`, id)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	if !rows.Next() {
		return nil, fmt.Errorf("record not found")
	}
	return scanDeath(rows)
}

// ListDeaths returns rows matching the search term (name / number / date /
// serial). An empty search returns everything, newest first.
func (db *DB) ListDeaths(search string) ([]*model.DeathExtract, error) {
	q := `SELECT ` + deathCols + ` FROM death_extract`
	var args []interface{}
	if s := strings.TrimSpace(search); s != "" {
		like := "%" + s + "%"
		q += ` WHERE name_of_dead_person LIKE ? OR number LIKE ? OR serial_no LIKE ?
			OR date_of_death LIKE ? OR place_of_death LIKE ?`
		args = []interface{}{like, like, like, like, like}
	}
	q += ` ORDER BY id DESC`
	rows, err := db.conn.Query(q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []*model.DeathExtract
	for rows.Next() {
		d, err := scanDeath(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, d)
	}
	return out, rows.Err()
}

func (db *DB) DeleteDeath(id int64) error {
	_, err := db.conn.Exec(`DELETE FROM death_extract WHERE id=?`, id)
	return err
}

// ----------------------------------------------------------------------------
// Marriage CRUD (parent + two party rows)
// ----------------------------------------------------------------------------

func (db *DB) SaveMarriage(m *model.MarriageReturn) error {
	now := nowStr()
	tx, err := db.conn.Begin()
	if err != nil {
		return err
	}
	if m.ID == 0 {
		m.CreatedAt = now
		m.UpdatedAt = now
		res, err := tx.Exec(`INSERT INTO marriage_return (
			serial_no, number, when_married, place_solemnized, witnesses,
			signature_of_licensee, witness_date, prepared_by, checked_by,
			registrar_name, created_at, updated_at)
			VALUES (?,?,?,?,?,?,?,?,?,?,?,?)`,
			m.SerialNo, m.Number, m.WhenMarried, m.PlaceSolemnized, m.Witnesses,
			m.SignatureOfLicensee, m.WitnessDate, m.PreparedBy, m.CheckedBy,
			m.RegistrarName, m.CreatedAt, m.UpdatedAt)
		if err != nil {
			tx.Rollback()
			return err
		}
		m.ID, _ = res.LastInsertId()
	} else {
		m.UpdatedAt = now
		if _, err := tx.Exec(`UPDATE marriage_return SET
			serial_no=?, number=?, when_married=?, place_solemnized=?, witnesses=?,
			signature_of_licensee=?, witness_date=?, prepared_by=?, checked_by=?,
			registrar_name=?, updated_at=? WHERE id=?`,
			m.SerialNo, m.Number, m.WhenMarried, m.PlaceSolemnized, m.Witnesses,
			m.SignatureOfLicensee, m.WitnessDate, m.PreparedBy, m.CheckedBy,
			m.RegistrarName, m.UpdatedAt, m.ID); err != nil {
			tx.Rollback()
			return err
		}
		// Replace party rows wholesale — simplest and safe for two children.
		if _, err := tx.Exec(`DELETE FROM marriage_party WHERE marriage_id=?`, m.ID); err != nil {
			tx.Rollback()
			return err
		}
	}
	m.PartyA.Side = "A"
	m.PartyB.Side = "B"
	for _, p := range []*model.MarriageParty{&m.PartyA, &m.PartyB} {
		if _, err := tx.Exec(`INSERT INTO marriage_party (
			marriage_id, side, name_of_party, surname, age, condition,
			rank_or_profession, residence_at_marriage, fathers_name,
			signature_contracting_party)
			VALUES (?,?,?,?,?,?,?,?,?,?)`,
			m.ID, p.Side, p.NameOfParty, p.Surname, p.Age, p.Condition,
			p.RankOrProfession, p.ResidenceAtMarriage, p.FathersName,
			p.SignatureContractingParty); err != nil {
			tx.Rollback()
			return err
		}
	}
	return tx.Commit()
}

func (db *DB) loadParties(m *model.MarriageReturn) error {
	rows, err := db.conn.Query(`SELECT id, marriage_id, side, name_of_party, surname,
		age, condition, rank_or_profession, residence_at_marriage, fathers_name,
		signature_contracting_party FROM marriage_party WHERE marriage_id=?`, m.ID)
	if err != nil {
		return err
	}
	defer rows.Close()
	for rows.Next() {
		p := model.MarriageParty{}
		if err := rows.Scan(&p.ID, &p.MarriageID, &p.Side, &p.NameOfParty, &p.Surname,
			&p.Age, &p.Condition, &p.RankOrProfession, &p.ResidenceAtMarriage,
			&p.FathersName, &p.SignatureContractingParty); err != nil {
			return err
		}
		if p.Side == "B" {
			m.PartyB = p
		} else {
			m.PartyA = p
		}
	}
	return rows.Err()
}

const marriageCols = `id, serial_no, number, when_married, place_solemnized, witnesses,
	signature_of_licensee, witness_date, prepared_by, checked_by, registrar_name,
	created_at, updated_at`

func scanMarriage(rows *sql.Rows) (*model.MarriageReturn, error) {
	m := &model.MarriageReturn{}
	err := rows.Scan(&m.ID, &m.SerialNo, &m.Number, &m.WhenMarried, &m.PlaceSolemnized,
		&m.Witnesses, &m.SignatureOfLicensee, &m.WitnessDate, &m.PreparedBy, &m.CheckedBy,
		&m.RegistrarName, &m.CreatedAt, &m.UpdatedAt)
	return m, err
}

func (db *DB) GetMarriage(id int64) (*model.MarriageReturn, error) {
	rows, err := db.conn.Query(`SELECT `+marriageCols+` FROM marriage_return WHERE id=?`, id)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	if !rows.Next() {
		return nil, fmt.Errorf("record not found")
	}
	m, err := scanMarriage(rows)
	if err != nil {
		return nil, err
	}
	rows.Close()
	if err := db.loadParties(m); err != nil {
		return nil, err
	}
	return m, nil
}

func (db *DB) ListMarriages(search string) ([]*model.MarriageReturn, error) {
	q := `SELECT ` + marriageCols + ` FROM marriage_return`
	var args []interface{}
	if s := strings.TrimSpace(search); s != "" {
		like := "%" + s + "%"
		// Match parent fields or either party name via subquery.
		q += ` WHERE number LIKE ? OR serial_no LIKE ? OR when_married LIKE ?
			OR id IN (SELECT marriage_id FROM marriage_party WHERE name_of_party LIKE ? OR surname LIKE ?)`
		args = []interface{}{like, like, like, like, like}
	}
	q += ` ORDER BY id DESC`
	rows, err := db.conn.Query(q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []*model.MarriageReturn
	for rows.Next() {
		m, err := scanMarriage(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, m)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	rows.Close()
	// Load parties for each (small N; fine to do per-row).
	for _, m := range out {
		if err := db.loadParties(m); err != nil {
			return nil, err
		}
	}
	return out, nil
}

func (db *DB) DeleteMarriage(id int64) error {
	// ON DELETE CASCADE removes party rows.
	_, err := db.conn.Exec(`DELETE FROM marriage_return WHERE id=?`, id)
	return err
}

// ----------------------------------------------------------------------------
// model.Baptism CRUD
// ----------------------------------------------------------------------------

func (db *DB) SaveBaptism(b *model.Baptism) error {
	now := nowStr()
	if b.ID == 0 {
		b.CreatedAt = now
		b.UpdatedAt = now
		res, err := db.conn.Exec(`INSERT INTO baptism (
			number, when_baptized, said_to_be_born, christian_name, surname_former_name,
			sex, father_name, mother_name, trade_or_profession, names_of_godparents,
			where_baptized, signature_by_whom_baptized, baptized_by_name, witness_date,
			prepared_by, checked_by, created_at, updated_at)
			VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
			b.Number, b.WhenBaptized, b.SaidToBeBorn, b.ChristianName, b.SurnameFormerName,
			b.Sex, b.FatherName, b.MotherName, b.TradeOrProfession, b.NamesOfGodparents,
			b.WhereBaptized, b.SignatureByWhomBaptized, b.BaptizedByName, b.WitnessDate,
			b.PreparedBy, b.CheckedBy, b.CreatedAt, b.UpdatedAt)
		if err != nil {
			return err
		}
		b.ID, _ = res.LastInsertId()
		return nil
	}
	b.UpdatedAt = now
	_, err := db.conn.Exec(`UPDATE baptism SET
		number=?, when_baptized=?, said_to_be_born=?, christian_name=?, surname_former_name=?,
		sex=?, father_name=?, mother_name=?, trade_or_profession=?, names_of_godparents=?,
		where_baptized=?, signature_by_whom_baptized=?, baptized_by_name=?, witness_date=?,
		prepared_by=?, checked_by=?, updated_at=? WHERE id=?`,
		b.Number, b.WhenBaptized, b.SaidToBeBorn, b.ChristianName, b.SurnameFormerName,
		b.Sex, b.FatherName, b.MotherName, b.TradeOrProfession, b.NamesOfGodparents,
		b.WhereBaptized, b.SignatureByWhomBaptized, b.BaptizedByName, b.WitnessDate,
		b.PreparedBy, b.CheckedBy, b.UpdatedAt, b.ID)
	return err
}

const baptismCols = `id, number, when_baptized, said_to_be_born, christian_name,
	surname_former_name, sex, father_name, mother_name, trade_or_profession,
	names_of_godparents, where_baptized, signature_by_whom_baptized, baptized_by_name,
	witness_date, prepared_by, checked_by, created_at, updated_at`

func scanBaptism(rows *sql.Rows) (*model.Baptism, error) {
	b := &model.Baptism{}
	err := rows.Scan(&b.ID, &b.Number, &b.WhenBaptized, &b.SaidToBeBorn, &b.ChristianName,
		&b.SurnameFormerName, &b.Sex, &b.FatherName, &b.MotherName, &b.TradeOrProfession,
		&b.NamesOfGodparents, &b.WhereBaptized, &b.SignatureByWhomBaptized, &b.BaptizedByName,
		&b.WitnessDate, &b.PreparedBy, &b.CheckedBy, &b.CreatedAt, &b.UpdatedAt)
	return b, err
}

func (db *DB) GetBaptism(id int64) (*model.Baptism, error) {
	rows, err := db.conn.Query(`SELECT `+baptismCols+` FROM baptism WHERE id=?`, id)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	if !rows.Next() {
		return nil, fmt.Errorf("record not found")
	}
	return scanBaptism(rows)
}

func (db *DB) ListBaptisms(search string) ([]*model.Baptism, error) {
	q := `SELECT ` + baptismCols + ` FROM baptism`
	var args []interface{}
	if s := strings.TrimSpace(search); s != "" {
		like := "%" + s + "%"
		q += ` WHERE christian_name LIKE ? OR surname_former_name LIKE ? OR number LIKE ?
			OR when_baptized LIKE ? OR father_name LIKE ?`
		args = []interface{}{like, like, like, like, like}
	}
	q += ` ORDER BY id DESC`
	rows, err := db.conn.Query(q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []*model.Baptism
	for rows.Next() {
		b, err := scanBaptism(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, b)
	}
	return out, rows.Err()
}

func (db *DB) DeleteBaptism(id int64) error {
	_, err := db.conn.Exec(`DELETE FROM baptism WHERE id=?`, id)
	return err
}
