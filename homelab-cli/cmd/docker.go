package cmd

import (
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/spf13/cobra"
)

// profileFlag is the value of the -p / --profile persistent flag on dockerCmd.
var profileFlag string

var dockerCmd = &cobra.Command{
	Use:   "docker",
	Short: "Manage homelab docker compose services",
}

func init() {
	dockerCmd.PersistentFlags().StringVarP(&profileFlag, "profile", "p", "", "docker compose profile to activate")
	_ = dockerCmd.RegisterFlagCompletionFunc("profile", func(_ *cobra.Command, _ []string, _ string) ([]string, cobra.ShellCompDirective) {
		cache, err := loadCache(repoRoot)
		if err != nil {
			return nil, cobra.ShellCompDirectiveNoFileComp
		}
		return cache.Profiles, cobra.ShellCompDirectiveNoFileComp
	})
	rootCmd.AddCommand(dockerCmd)
}

// addServiceFlag adds a repeatable -s/--service flag with tab completion to a command.
// Each var must be declared per-command so flags don't bleed between subcommands.
func addServiceFlag(cmd *cobra.Command, target *[]string) {
	cmd.Flags().StringArrayVarP(target, "service", "s", nil, "target one or more services (repeatable)")
	_ = cmd.RegisterFlagCompletionFunc("service", func(_ *cobra.Command, _ []string, _ string) ([]string, cobra.ShellCompDirective) {
		cache, err := loadCache(repoRoot)
		if err != nil {
			return nil, cobra.ShellCompDirectiveNoFileComp
		}
		return cache.Services, cobra.ShellCompDirectiveNoFileComp
	})
}

// composeBase returns the base docker compose args including project-directory and optional profile.
func composeBase() []string {
	args := []string{
		"compose",
		"--project-directory", repoRoot,
	}
	if profileFlag != "" {
		args = append(args, "--profile", profileFlag)
	}
	return args
}

// runCompose runs docker compose with the provided extra args, streaming stdout/stderr.
func runCompose(args ...string) error {
	base := composeBase()
	full := append(base, args...)
	display := append([]string{"docker"}, full...)

	if resolveOnly {
		fmt.Fprintln(os.Stdout, formatCommand(display))
		return nil
	}

	c := exec.Command("docker", full...)
	c.Stdout = os.Stdout
	c.Stderr = os.Stderr
	c.Stdin = os.Stdin
	return c.Run()
}

// composeOutput runs a docker compose command and captures its stdout.
func composeOutput(args ...string) (string, error) {
	base := composeBase()
	full := append(base, args...)
	out, err := exec.Command("docker", full...).Output()
	return string(out), err
}

// resolveServices returns the explicit service list to target. If services are
// provided they are used directly. If a profile is set but no services, the
// services for that profile are resolved dynamically via docker compose config.
// If neither is set, nil is returned (compose will target all services).
func resolveServices(services []string) ([]string, error) {
	if len(services) > 0 {
		return services, nil
	}
	if profileFlag == "" {
		return nil, nil
	}
	out, err := composeOutput("config", "--services")
	if err != nil {
		return nil, fmt.Errorf("resolving services for profile %q: %w", profileFlag, err)
	}
	var resolved []string
	for _, line := range strings.Fields(out) {
		if line != "" {
			resolved = append(resolved, line)
		}
	}
	if len(resolved) == 0 {
		return nil, fmt.Errorf("no services found for profile %q", profileFlag)
	}
	return resolved, nil
}

func formatCommand(args []string) string {
	quoted := make([]string, 0, len(args))
	for _, arg := range args {
		if strings.ContainsAny(arg, " \t\n\"'`$\\") {
			quoted = append(quoted, fmt.Sprintf("%q", arg))
			continue
		}
		quoted = append(quoted, arg)
	}
	return strings.Join(quoted, " ")
}
