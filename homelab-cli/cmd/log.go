package cmd

import (
	"fmt"
	"os"
)

const (
	ansiBlue  = "\033[34m"
	ansiReset = "\033[0m"
)

// logInfo prints a [jdc]-prefixed informational message to stderr.
func logInfo(format string, args ...any) {
	fmt.Fprintf(os.Stderr, "%s[jdc]%s %s\n", ansiBlue, ansiReset, fmt.Sprintf(format, args...))
}
