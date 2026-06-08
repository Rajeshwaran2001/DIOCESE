//go:build windows

package printing

import (
	"fmt"
	"math"
	"syscall"
	"unsafe"

	"diocese-certs/internal/config"
	"diocese-certs/internal/model"

	"github.com/lxn/win"
)

// ----------------------------------------------------------------------------
// GDI OVERLAY PRINTING ENGINE
//
// The blank forms are already printed on paper. We open a Device Context (DC)
// on the printer and draw ONLY the variable values at absolute millimetre
// positions measured from the top-left corner of the physical page.
//
// THE COORDINATE MATH (read this before touching it):
//   * Layout coordinates are in millimetres from the PHYSICAL top-left corner.
//   * GDI's drawing origin (0,0) is the top-left of the PRINTABLE area, which
//     sits a few millimetres in from the physical edge (the printer's hardware
//     margin). GetDeviceCaps(PHYSICALOFFSETX/Y) gives that inset in pixels.
//   * Pixels-per-mm = GetDeviceCaps(LOGPIXELSX/Y) / 25.4   (dots per inch / 25.4)
//   * Therefore:
//       deviceX = round(mm_x * dpiX/25.4) - physicalOffsetX
//       deviceY = round(mm_y * dpiY/25.4) - physicalOffsetY
//   * The user's per-form calibration (X/Y in mm) is added to mm_x/mm_y first.
// ----------------------------------------------------------------------------

const mmPerInch = 25.4

// printerMetrics holds everything we need to convert mm -> device pixels.
type printerMetrics struct {
	dpiX, dpiY int32
	offsetX    int32 // PHYSICALOFFSETX in pixels
	offsetY    int32 // PHYSICALOFFSETY in pixels
}

func readMetrics(hdc win.HDC) printerMetrics {
	return printerMetrics{
		dpiX:    win.GetDeviceCaps(hdc, win.LOGPIXELSX),
		dpiY:    win.GetDeviceCaps(hdc, win.LOGPIXELSY),
		offsetX: win.GetDeviceCaps(hdc, win.PHYSICALOFFSETX),
		offsetY: win.GetDeviceCaps(hdc, win.PHYSICALOFFSETY),
	}
}

// deviceXY converts a millimetre coordinate (already including calibration) to
// printer device pixels.
func (m printerMetrics) deviceXY(xmm, ymm float64) (int32, int32) {
	px := int32(math.Round(xmm*float64(m.dpiX)/mmPerInch)) - m.offsetX
	py := int32(math.Round(ymm*float64(m.dpiY)/mmPerInch)) - m.offsetY
	return px, py
}

// ----------------------------------------------------------------------------
// Opening a printer DC
// ----------------------------------------------------------------------------

var (
	winspool              = syscall.NewLazyDLL("winspool.drv")
	procGetDefaultPrinter = winspool.NewProc("GetDefaultPrinterW")
)

// defaultPrinterName returns the system default printer name, or "".
func defaultPrinterName() string {
	var size uint32 = 0
	// First call to get required buffer size.
	procGetDefaultPrinter.Call(0, uintptr(unsafe.Pointer(&size)))
	if size == 0 {
		return ""
	}
	buf := make([]uint16, size)
	r, _, _ := procGetDefaultPrinter.Call(
		uintptr(unsafe.Pointer(&buf[0])),
		uintptr(unsafe.Pointer(&size)),
	)
	if r == 0 {
		return ""
	}
	return syscall.UTF16ToString(buf)
}

// openPrinterDC returns a printer DC for the configured/default printer.
// The caller MUST call win.DeleteDC on the result.
func openPrinterDC(cfg *config.Config) (win.HDC, string, error) {
	name := cfg.PrinterName
	if name == "" {
		name = defaultPrinterName()
	}
	if name == "" {
		return 0, "", fmt.Errorf("no printer found. Please install or select a printer in Settings")
	}
	devPtr, err := syscall.UTF16PtrFromString(name)
	if err != nil {
		return 0, name, err
	}
	hdc := win.CreateDC(nil, devPtr, nil, nil)
	if hdc == 0 {
		return 0, name, fmt.Errorf("could not open printer %q", name)
	}
	return hdc, name, nil
}

// ----------------------------------------------------------------------------
// Font
// ----------------------------------------------------------------------------

// createFont builds a printer-DPI-scaled font. pointSize is in typographic
// points (1/72 inch).
func createFont(metrics printerMetrics, name string, pointSize int) win.HFONT {
	if name == "" {
		name = "Times New Roman"
	}
	if pointSize <= 0 {
		pointSize = 11
	}
	lf := win.LOGFONT{
		// Negative height requests a font of that CHARACTER height in device units.
		LfHeight:         -int32(math.Round(float64(pointSize) * float64(metrics.dpiY) / 72.0)),
		LfWeight:         win.FW_NORMAL,
		LfCharSet:        win.DEFAULT_CHARSET,
		LfOutPrecision:   win.OUT_TT_PRECIS,
		LfClipPrecision:  win.CLIP_DEFAULT_PRECIS,
		LfQuality:        win.PROOF_QUALITY,
		LfPitchAndFamily: win.DEFAULT_PITCH | win.FF_ROMAN,
	}
	// Copy the (UTF-16) face name into the fixed-size LfFaceName array.
	face, _ := syscall.UTF16FromString(name)
	for i := 0; i < len(face) && i < len(lf.LfFaceName); i++ {
		lf.LfFaceName[i] = face[i]
	}
	return win.CreateFontIndirect(&lf)
}

// ----------------------------------------------------------------------------
// The core draw routine
// ----------------------------------------------------------------------------

// drawText writes one UTF-16 string at device pixel (x,y).
func drawText(hdc win.HDC, x, y int32, s string) {
	if s == "" {
		return
	}
	u, err := syscall.UTF16FromString(s)
	if err != nil {
		return
	}
	// UTF16FromString appends a trailing NUL; exclude it from the count.
	n := int32(len(u) - 1)
	if n <= 0 {
		return
	}
	win.TextOut(hdc, x, y, &u[0], n)
}

// printItems performs the full StartDoc..EndDoc cycle, drawing the supplied
// TextItems with the given calibration offset applied.
func printItems(cfg *config.Config, docName string, formID string, items []TextItem) error {
	hdc, _, err := openPrinterDC(cfg)
	if err != nil {
		return err
	}
	defer win.DeleteDC(hdc)

	metrics := readMetrics(hdc)
	cal := cfg.Calibration[formID]

	// Build & select font; remember the old one to restore + delete.
	hfont := createFont(metrics, cfg.FontName, cfg.FontPointSize)
	if hfont != 0 {
		old := win.SelectObject(hdc, win.HGDIOBJ(hfont))
		defer func() {
			win.SelectObject(hdc, old)
			win.DeleteObject(win.HGDIOBJ(hfont))
		}()
	}
	win.SetBkMode(hdc, win.TRANSPARENT)
	win.SetTextColor(hdc, win.COLORREF(0x00000000)) // black

	// StartDoc / StartPage.
	docPtr, _ := syscall.UTF16PtrFromString(docName)
	di := win.DOCINFO{
		CbSize:      int32(unsafe.Sizeof(win.DOCINFO{})),
		LpszDocName: docPtr,
	}
	if win.StartDoc(hdc, &di) <= 0 {
		return fmt.Errorf("StartDoc failed (printer rejected the job)")
	}
	if win.StartPage(hdc) <= 0 {
		win.EndDoc(hdc)
		return fmt.Errorf("StartPage failed")
	}

	for _, it := range items {
		x, y := metrics.deviceXY(it.Xmm+cal.XmmOffset, it.Ymm+cal.YmmOffset)
		drawText(hdc, x, y, it.Text)
	}

	if win.EndPage(hdc) <= 0 {
		win.EndDoc(hdc)
		return fmt.Errorf("EndPage failed")
	}
	if win.EndDoc(hdc) <= 0 {
		return fmt.Errorf("EndDoc failed")
	}
	return nil
}

// ----------------------------------------------------------------------------
// Public print entry points (used by the UI)
// ----------------------------------------------------------------------------

func PrintDeath(cfg *config.Config, d *model.DeathExtract) error {
	return printItems(cfg, "Death Extract", "death", buildDeathItems(d))
}

func PrintMarriage(cfg *config.Config, m *model.MarriageReturn) error {
	return printItems(cfg, "Marriage Return", "marriage", buildMarriageItems(m))
}

func PrintBaptism(cfg *config.Config, b *model.Baptism) error {
	return printItems(cfg, "model.Baptism Certificate", "baptism", buildBaptismItems(b))
}

// ----------------------------------------------------------------------------
// Alignment test print
//
// Prints, on PLAIN paper, the field positions for a given form (a short label
// and a tick at each coordinate) plus a 10 mm reference grid of crosshairs.
// The clerk lays this over a real pre-printed form against the light and reads
// off how far each value is from where it should sit, then enters X/Y offsets.
// ----------------------------------------------------------------------------

func PrintAlignmentTest(cfg *config.Config, formID string) error {
	hdc, _, err := openPrinterDC(cfg)
	if err != nil {
		return err
	}
	defer win.DeleteDC(hdc)

	metrics := readMetrics(hdc)
	cal := cfg.Calibration[formID]

	hfont := createFont(metrics, cfg.FontName, 8) // small font for tick labels
	if hfont != 0 {
		old := win.SelectObject(hdc, win.HGDIOBJ(hfont))
		defer func() {
			win.SelectObject(hdc, old)
			win.DeleteObject(win.HGDIOBJ(hfont))
		}()
	}
	win.SetBkMode(hdc, win.TRANSPARENT)
	win.SetTextColor(hdc, win.COLORREF(0x00000000))

	docPtr, _ := syscall.UTF16PtrFromString("Alignment Test")
	di := win.DOCINFO{CbSize: int32(unsafe.Sizeof(win.DOCINFO{})), LpszDocName: docPtr}
	if win.StartDoc(hdc, &di) <= 0 {
		return fmt.Errorf("StartDoc failed")
	}
	if win.StartPage(hdc) <= 0 {
		win.EndDoc(hdc)
		return fmt.Errorf("StartPage failed")
	}

	// Page extent in mm (A4 default, Letter optional).
	pageWmm, pageHmm := 210.0, 297.0
	if cfg.PaperSize == "Letter" {
		pageWmm, pageHmm = 215.9, 279.4
	}

	// 1) 10 mm reference grid of small crosshairs with mm labels along edges.
	for x := 10.0; x < pageWmm; x += 10.0 {
		for y := 10.0; y < pageHmm; y += 10.0 {
			cx, cy := metrics.deviceXY(x, y)
			drawCross(hdc, cx, cy, metrics)
		}
	}
	// Axis labels every 20 mm.
	for x := 20.0; x < pageWmm; x += 20.0 {
		px, py := metrics.deviceXY(x, 6)
		drawText(hdc, px, py, fmt.Sprintf("%dmm", int(x)))
	}
	for y := 20.0; y < pageHmm; y += 20.0 {
		px, py := metrics.deviceXY(2, y)
		drawText(hdc, px, py, fmt.Sprintf("%dmm", int(y)))
	}

	// 2) The actual field positions for this form (with calibration applied),
	//    each marked with a tick and its field name, using SAMPLE text so the
	//    clerk sees the real layout.
	for _, it := range alignmentItems(formID) {
		x, y := metrics.deviceXY(it.Xmm+cal.XmmOffset, it.Ymm+cal.YmmOffset)
		drawText(hdc, x, y, it.Text)
	}

	if win.EndPage(hdc) <= 0 {
		win.EndDoc(hdc)
		return fmt.Errorf("EndPage failed")
	}
	if win.EndDoc(hdc) <= 0 {
		return fmt.Errorf("EndDoc failed")
	}
	return nil
}

// drawCross draws a small + crosshair (about 2 mm arms) centred at device x,y.
func drawCross(hdc win.HDC, x, y int32, m printerMetrics) {
	arm := int32(math.Round(1.0 * float64(m.dpiX) / mmPerInch)) // 1 mm arm
	pen := win.GetStockObject(win.BLACK_PEN)
	old := win.SelectObject(hdc, pen)
	win.MoveToEx(hdc, int(x-arm), int(y), nil)
	win.LineTo(hdc, x+arm, y)
	win.MoveToEx(hdc, int(x), int(y-arm), nil)
	win.LineTo(hdc, x, y+arm)
	win.SelectObject(hdc, old)
}

// alignmentItems returns sample-text markers at every defined field position
// for the given form, so the alignment print shows the real layout.
func alignmentItems(formID string) []TextItem {
	switch formID {
	case "death":
		var out []TextItem
		for k, p := range deathLayout {
			out = append(out, TextItem{"[" + k + "]", p.Xmm, p.Ymm})
		}
		return out
	case "baptism":
		var out []TextItem
		for k, p := range baptismLayout {
			out = append(out, TextItem{"[" + k + "]", p.Xmm, p.Ymm})
		}
		return out
	case "marriage":
		var out []TextItem
		for k, y := range marriageRowY {
			out = append(out, TextItem{"[A:" + k + "]", marriagePartyAX, y})
			out = append(out, TextItem{"[B:" + k + "]", marriagePartyBX, y})
		}
		for k, p := range marriageSingle {
			out = append(out, TextItem{"[" + k + "]", p.Xmm, p.Ymm})
		}
		return out
	}
	return nil
}
