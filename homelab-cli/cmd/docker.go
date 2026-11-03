package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"sort"
	"strings"

	"github.com/spf13/cobra"
)

// profileFlag is the value of the -p / --profile persistent flag on dockerCmd.
var profileFlag string

var dockerCmd = &cobra.Command{
	Use:   "docker",
	Short: "Manage homelab docker compose services",
}

type composeConfig struct {
	Services map[string]composeService `json:"services"`
}

type composeService struct {
	ContainerName string   `json:"container_name"`
	Profiles      []string `json:"profiles"`
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

// composeBaseWithProfile returns the base docker compose args including project-directory
// and the provided optional profile.
func composeBaseWithProfile(profile string) []string {
	args := []string{
		"compose",
		"--project-directory", repoRoot,
	}
	if profile != "" {
		args = append(args, "--profile", profile)
	}
	return args
}

// composeBase returns the base docker compose args including project-directory and optional profile.
func composeBase() []string {
	return composeBaseWithProfile(profileFlag)
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

// composeOutputWithProfile captures stdout for commands that intentionally need a
// specific profile instead of the user-provided profile flag.
func composeOutputWithProfile(profile string, args ...string) (string, error) {
	base := composeBaseWithProfile(profile)
	full := append(base, args...)
	out, err := exec.Command("docker", full...).Output()
	return string(out), err
}

func loadComposeServices() (map[string]composeService, error) {
	profilesOut, err := composeOutputWithProfile("", "config", "--profiles")
	if err != nil {
		return nil, err
	}
	out, err := composeOutputWithProfile("", composeConfigJSONArgs(strings.Fields(profilesOut))...)
	if err != nil {
		return nil, err
	}
	var cfg composeConfig
	if err := json.Unmarshal([]byte(out), &cfg); err != nil {
		return nil, err
	}
	if cfg.Services == nil {
		cfg.Services = map[string]composeService{}
	}
	return cfg.Services, nil
}

func composeConfigJSONArgs(profiles []string) []string {
	args := make([]string, 0, len(profiles)*2+3)
	for _, profile := range profiles {
		if profile != "" {
			args = append(args, "--profile", profile)
		}
	}
	return append(args, "config", "--format", "json")
}

func serviceNames(services map[string]composeService) []string {
	names := make([]string, 0, len(services))
	for name := range services {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

func profilesFromServices(services map[string]composeService) []string {
	profileSet := make(map[string]struct{})
	for _, svc := range services {
		for _, profile := range svc.Profiles {
			if profile != "" {
				profileSet[profile] = struct{}{}
			}
		}
	}

	profiles := make([]string, 0, len(profileSet))
	for profile := range profileSet {
		profiles = append(profiles, profile)
	}
	sort.Strings(profiles)
	return profiles
}

func hasString(values []string, target string) bool {
	for _, value := range values {
		if value == target {
			return true
		}
	}
	return false
}

func servicesForProfile(profile string) ([]string, error) {
	services, err := loadComposeServices()
	if err != nil {
		return nil, fmt.Errorf("loading compose services: %w", err)
	}

	var resolved []string
	for name, svc := range services {
		if hasString(svc.Profiles, profile) {
			resolved = append(resolved, name)
		}
	}
	sort.Strings(resolved)
	if len(resolved) == 0 {
		return nil, fmt.Errorf("no services found for profile %q", profile)
	}
	return resolved, nil
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
	resolved, err := servicesForProfile(profileFlag)
	if err != nil {
		return nil, err
	}
	if resolveOnly {
		logInfo("Profile %q resolves to: %s", profileFlag, strings.Join(resolved, ", "))
	}
	return resolved, nil
}

func resolveRequiredServices(commandName string, services []string) ([]string, error) {
	resolved, err := resolveServices(services)
	if err != nil {
		return nil, err
	}
	if len(resolved) == 0 {
		return nil, fmt.Errorf("for 'docker %s', target one or more services with -s or a profile with -p (use -p all for all profile-managed services)", commandName)
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
