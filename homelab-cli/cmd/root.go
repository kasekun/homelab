package cmd

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
)

// repoRoot is resolved once at startup by walking up from cwd.
var repoRoot string
var resolveOnly bool

var rootCmd = &cobra.Command{
	Use:   "jdc",
	Short: "jdc — homelab CLI for managing self-hosted services",
	Long: `jdc wraps docker compose operations and homelab scripts
with tab completion and a consistent flag interface.

Run from any directory inside the homelab repo.`,
	SilenceUsage: true,
}

// Execute is the entry point called from main.
func Execute() {
	if err := rootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}

func init() {
	cobra.OnInitialize(resolveRepoRoot)
	rootCmd.PersistentFlags().BoolVar(&resolveOnly, "resolve-only", false, "print resolved command without executing")
}

// resolveRepoRoot walks up from cwd looking for docker-compose.yaml,
// mirroring how git finds .git. The resolved repo root path is stored in repoRoot.
func resolveRepoRoot() {
	cwd, err := os.Getwd()
	if err != nil {
		fmt.Fprintln(os.Stderr, "error: cannot determine working directory:", err)
		os.Exit(1)
	}

	dir := cwd
	for {
		candidate := filepath.Join(dir, "docker-compose.yaml")
		if _, err := os.Stat(candidate); err == nil {
			repoRoot = dir
			return
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			fmt.Fprintln(os.Stderr, "error: could not find docker-compose.yaml — run jdc from inside the homelab repo")
			os.Exit(1)
		}
		dir = parent
	}
}
