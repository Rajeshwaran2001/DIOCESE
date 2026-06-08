//go:build windows

// Command diocesecerts is the Windows desktop entry point for the Diocese of
// Madurai Ramnad Certificate Manager. All behaviour lives in internal/ui; this
// file just hands control to it.
package main

import "diocese-certs/internal/ui"

func main() {
	ui.Run()
}
