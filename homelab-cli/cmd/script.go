package cmd

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"

	"github.com/spf13/cobra"
)

// scriptYes is the -y/--yes flag shared across script subcommands that prompt for confirmation.
var scriptYes bool

type scriptEntry struct {
	short    string
	acceptsY bool
	run      func(yes bool) error
}

func init() {

	scriptCmd := &cobra.Command{
		Use:       "script <name> [args...]",
		Short:     "Run a homelab setup or maintenance script",
		ValidArgs: scriptNameList(),
		Args:      cobra.MinimumNArgs(1),
		Example: `  jdc script check-env
  jdc script check-space
  jdc script copy-env
  jdc script copy-env -y
  jdc script traefik-acme -y
  jdc script ufw-setup -y
  jdc script init-homelab -y`,
		RunE: func(cmd *cobra.Command, args []string) error {
			name := args[0]
			scripts := buildScripts()
			entry, ok := scripts[name]
			if !ok {
				names := make([]string, 0, len(scripts))
				for k := range scripts {
					names = append(names, k)
				}
				sort.Strings(names)
				return fmt.Errorf("unknown script %q — known scripts: %s", name, strings.Join(names, ", "))
			}
			return entry.run(scriptYes)
		},
	}

	scriptCmd.Flags().BoolVarP(&scriptYes, "yes", "y", false, "skip confirmation prompts")
	rootCmd.AddCommand(scriptCmd)
}

// scriptNameList returns the hard-coded list of script names for completion.
// This is called at init time so it must not reference repoRoot.
func scriptNameList() []string {
	names := []string{
		"traefik-acme",
		"ufw-setup",
		"ufw-remove",
		"copy-env",
		"check-env",
		"check-space",
		"backup",
		"check-vpn",
		"create-databases",
		"init-homelab",
	}
	sort.Strings(names)
	return names
}

// buildScripts constructs the dispatch map at call time so repoRoot is resolved.
func buildScripts() map[string]scriptEntry {
	return map[string]scriptEntry{
		"traefik-acme": {
			short:    "Initialise traefik ACME (acme.json)",
			acceptsY: true,
			run: func(yes bool) error {
				script := filepath.Join(repoRoot, "jdc", "scripts", "initialise-traefik-acme.sh")
				return shellOut(script, yes)
			},
		},
		"ufw-setup": {
			short:    "Configure UFW rules for homelab traffic",
			acceptsY: true,
			run: func(yes bool) error {
				script := filepath.Join(repoRoot, "jdc", "scripts", "setup_ufw_rules.sh")
				return shellOut(script, yes)
			},
		},
		"ufw-remove": {
			short:    "Remove UFW rules added by ufw-setup",
			acceptsY: true,
			run: func(yes bool) error {
				script := filepath.Join(repoRoot, "jdc", "scripts", "ufw_rules_remove.sh")
				return shellOut(script, yes)
			},
		},
		"copy-env": {
			short:    "Copy .env-example to .env (native Go)",
			acceptsY: true,
			run:      runCopyEnv,
		},
		"check-env": {
			short: "Validate required variables are set in .env (native Go)",
			run:   func(_ bool) error { return runCheckEnv() },
		},
		"check-space": {
			short: "Show disk usage for MEDIA_DIRECTORY (native Go)",
			run:   func(_ bool) error { return runCheckSpace() },
		},
		"backup": {
			short: "Run the homelab backup script",
			run: func(_ bool) error {
				return shellOut(filepath.Join(repoRoot, "scripts", "backup.sh"), false)
			},
		},
		"check-vpn": {
			short: "Check whether the VPN is active",
			run: func(_ bool) error {
				return shellOut(filepath.Join(repoRoot, "scripts", "check_vpn.sh"), false)
			},
		},
		"create-databases": {
			short: "Create required databases",
			run: func(_ bool) error {
				return shellOut(filepath.Join(repoRoot, "scripts", "create-databases.sh"), false)
			},
		},
		"init-homelab": {
			short:    "Full bootstrap: copy-env → check-env → check-space → traefik-acme → ufw-setup",
			acceptsY: true,
			run: func(yes bool) error {
				scripts := buildScripts()
				sequence := []string{"copy-env", "check-env", "check-space", "traefik-acme", "ufw-setup"}
				for _, name := range sequence {
					logInfo("Running script: %s", name)
					if err := scripts[name].run(yes); err != nil {
						return fmt.Errorf("init-homelab failed at %q: %w", name, err)
					}
				}
				return nil
			},
		},
	}
}

// shellOut executes a shell script. If yes is true it sets the
// JDC_YES=1 env var so scripts can skip interactive prompts.
func shellOut(script string, yes bool) error {
	if _, err := os.Stat(script); err != nil {
		return fmt.Errorf("script not found: %s", script)
	}
	cmd := exec.Command("bash", script)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	if yes {
		cmd.Env = append(os.Environ(), "JDC_YES=1")
	} else {
		cmd.Env = os.Environ()
	}
	return cmd.Run()
}

// runCopyEnv copies .env-example → .env (native Go).
func runCopyEnv(yes bool) error {
	src := filepath.Join(repoRoot, ".env-example")
	dst := filepath.Join(repoRoot, ".env")

	if _, err := os.Stat(dst); err == nil && !yes {
		return fmt.Errorf(".env already exists — pass -y to overwrite")
	}

	data, err := os.ReadFile(src)
	if err != nil {
		return fmt.Errorf("reading %s: %w", src, err)
	}
	if err := os.WriteFile(dst, data, 0600); err != nil {
		return fmt.Errorf("writing %s: %w", dst, err)
	}
	logInfo("Copied %s → %s", src, dst)
	return nil
}

// runCheckEnv validates that non-empty-value lines in .env-example are also
// set (non-empty) in .env. It is a native Go reimplementation of the check.
func runCheckEnv() error {
	envFile := filepath.Join(repoRoot, ".env")
	exampleFile := filepath.Join(repoRoot, ".env-example")

	actual, err := parseEnvFile(envFile)
	if err != nil {
		return fmt.Errorf("reading .env: %w", err)
	}
	example, err := parseEnvFile(exampleFile)
	if err != nil {
		return fmt.Errorf("reading .env-example: %w", err)
	}

	var missing []string
	for key, exampleVal := range example {
		if exampleVal == "" {
			continue
		}
		if val, ok := actual[key]; !ok || strings.TrimSpace(val) == "" {
			missing = append(missing, key)
		}
	}
	sort.Strings(missing)

	if len(missing) > 0 {
		return fmt.Errorf("missing or empty required .env variables:\n  %s", strings.Join(missing, "\n  "))
	}
	logInfo(".env looks good — all required variables are set")
	return nil
}

// parseEnvFile reads KEY=VALUE pairs from a .env file, skipping comments and blanks.
func parseEnvFile(path string) (map[string]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	result := make(map[string]string)
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		val := strings.Trim(strings.TrimSpace(parts[1]), `"'`)
		result[key] = val
	}
	return result, scanner.Err()
}

// runCheckSpace prints df -h output for MEDIA_DIRECTORY from .env.
func runCheckSpace() error {
	envFile := filepath.Join(repoRoot, ".env")
	vars, err := parseEnvFile(envFile)
	if err != nil {
		return fmt.Errorf("reading .env: %w", err)
	}

	dir, ok := vars["MEDIA_DIRECTORY"]
	if !ok || dir == "" {
		return fmt.Errorf("MEDIA_DIRECTORY is not set in .env")
	}

	logInfo("Disk usage for MEDIA_DIRECTORY=%s", dir)
	cmd := exec.Command("df", "-h", dir)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}
