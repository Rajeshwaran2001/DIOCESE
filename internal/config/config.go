package config

import (
	"encoding/json"
	"os"
	"path/filepath"
)

// CalibrationOffset holds a per-form global print nudge, in millimetres.
// Positive X moves text right, positive Y moves text down.
type CalibrationOffset struct {
	XmmOffset float64 `json:"x_mm_offset"`
	YmmOffset float64 `json:"y_mm_offset"`
}

// Config is persisted as config.json next to the exe (falling back to
// %APPDATA%\DioceseCerts if the exe directory is not writable, e.g. when
// installed under Program Files).
type Config struct {
	// DataPath is the folder that holds the SQLite database file. It can be a
	// USB drive or a shared network folder. The DB file itself is always named
	// diocese.db inside this folder.
	DataPath string `json:"data_path"`

	// PaperSize is "A4" (default) or "Letter".
	PaperSize string `json:"paper_size"`

	// PrinterName, when non-empty, forces a specific printer. Empty = default
	// system printer.
	PrinterName string `json:"printer_name"`

	// FontName / FontPointSize control the overlay text. Times New Roman at
	// 11pt is a sensible default for these registry-style forms.
	FontName      string `json:"font_name"`
	FontPointSize int    `json:"font_point_size"`

	// Per-form calibration offsets, keyed by form id: "death", "marriage",
	// "baptism".
	Calibration map[string]CalibrationOffset `json:"calibration"`

	// configPath is where this struct was loaded from / will be saved to. Not
	// serialised.
	configPath string `json:"-"`
}

const dbFileName = "diocese.db"

// defaultConfig builds a fresh config rooted at the given data folder.
func defaultConfig(dataPath string) *Config {
	return &Config{
		DataPath:      dataPath,
		PaperSize:     "A4",
		PrinterName:   "",
		FontName:      "Times New Roman",
		FontPointSize: 11,
		Calibration: map[string]CalibrationOffset{
			"death":    {0, 0},
			"marriage": {0, 0},
			"baptism":  {0, 0},
		},
	}
}

// exeDir returns the directory containing the running executable.
func exeDir() string {
	exe, err := os.Executable()
	if err != nil {
		if wd, werr := os.Getwd(); werr == nil {
			return wd
		}
		return "."
	}
	return filepath.Dir(exe)
}

// appDataDir returns %APPDATA%\DioceseCerts, creating it if needed.
func appDataDir() string {
	base := os.Getenv("APPDATA")
	if base == "" {
		base = exeDir()
	}
	dir := filepath.Join(base, "DioceseCerts")
	_ = os.MkdirAll(dir, 0o755)
	return dir
}

// configSearchPaths returns the candidate config.json locations, in priority
// order. We prefer a config sitting next to the exe (portable / USB usage) and
// fall back to %APPDATA%.
func configSearchPaths() []string {
	return []string{
		filepath.Join(exeDir(), "config.json"),
		filepath.Join(appDataDir(), "config.json"),
	}
}

// writableConfigPath picks where a brand-new config should be written. We try
// the exe directory first (portable), but if it is not writable (Program Files
// without admin) we use %APPDATA%.
func writableConfigPath() string {
	exeCandidate := filepath.Join(exeDir(), "config.json")
	if isWritableDir(exeDir()) {
		return exeCandidate
	}
	return filepath.Join(appDataDir(), "config.json")
}

func isWritableDir(dir string) bool {
	probe := filepath.Join(dir, ".write_probe")
	f, err := os.OpenFile(probe, os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return false
	}
	_ = f.Close()
	_ = os.Remove(probe)
	return true
}

// LoadConfig finds and loads config.json, or creates a default one. The default
// data path is the folder where the config lives, so the DB sits alongside it.
func LoadConfig() (*Config, error) {
	for _, p := range configSearchPaths() {
		data, err := os.ReadFile(p)
		if err != nil {
			continue
		}
		cfg := &Config{}
		if err := json.Unmarshal(data, cfg); err != nil {
			// Corrupt config: don't lose the user's data, just start fresh
			// from a default but keep the same file location.
			cfg = defaultConfig(filepath.Dir(p))
		}
		cfg.configPath = p
		cfg.applyDefaults()
		return cfg, nil
	}

	// No config found anywhere: create a default.
	path := writableConfigPath()
	cfg := defaultConfig(filepath.Dir(path))
	cfg.configPath = path
	cfg.applyDefaults()
	if err := cfg.Save(); err != nil {
		return cfg, err
	}
	return cfg, nil
}

// applyDefaults backfills any missing fields so older config files keep working.
func (c *Config) applyDefaults() {
	if c.PaperSize == "" {
		c.PaperSize = "A4"
	}
	if c.FontName == "" {
		c.FontName = "Times New Roman"
	}
	if c.FontPointSize == 0 {
		c.FontPointSize = 11
	}
	if c.DataPath == "" {
		c.DataPath = filepath.Dir(c.configPath)
	}
	if c.Calibration == nil {
		c.Calibration = map[string]CalibrationOffset{}
	}
	for _, form := range []string{"death", "marriage", "baptism"} {
		if _, ok := c.Calibration[form]; !ok {
			c.Calibration[form] = CalibrationOffset{}
		}
	}
}

// Save writes the config back to disk (pretty-printed).
func (c *Config) Save() error {
	if c.configPath == "" {
		c.configPath = writableConfigPath()
	}
	if err := os.MkdirAll(filepath.Dir(c.configPath), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(c.configPath, data, 0o644)
}

// DBPath returns the full path to the SQLite database file.
func (c *Config) DBPath() string {
	return filepath.Join(c.DataPath, dbFileName)
}

// ConfigFilePath exposes where the config currently lives (for the UI).
func (c *Config) ConfigFilePath() string {
	return c.configPath
}
