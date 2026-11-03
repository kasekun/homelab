package cmd

import (
	"slices"
	"testing"
)

func TestComposeConfigJSONArgsEnablesEveryProfile(t *testing.T) {
	got := composeConfigJSONArgs([]string{"media", "all"})
	want := []string{"--profile", "media", "--profile", "all", "config", "--format", "json"}
	if !slices.Equal(got, want) {
		t.Fatalf("composeConfigJSONArgs() = %v, want %v", got, want)
	}
}

func TestComposeConfigJSONArgsAllowsNoProfiles(t *testing.T) {
	got := composeConfigJSONArgs(nil)
	want := []string{"config", "--format", "json"}
	if !slices.Equal(got, want) {
		t.Fatalf("composeConfigJSONArgs() = %v, want %v", got, want)
	}
}

func TestParseComposePSContainers(t *testing.T) {
	out := `{"Name":"sonarr","Service":"sonarr","State":"running","Status":"Up 1 hour"}
{"Name":"radarr","Service":"radarr","State":"exited","Status":"Exited (0)"}`

	got, err := parseComposePSContainers(out)
	if err != nil {
		t.Fatalf("parseComposePSContainers() error = %v", err)
	}
	if len(got) != 2 {
		t.Fatalf("parseComposePSContainers() returned %d containers, want 2", len(got))
	}
	if got[0].Name != "sonarr" || got[1].Status != "Exited (0)" {
		t.Fatalf("parseComposePSContainers() = %#v", got)
	}
}

func TestParseComposePSContainersAllowsEmptyOutput(t *testing.T) {
	got, err := parseComposePSContainers("")
	if err != nil {
		t.Fatalf("parseComposePSContainers() error = %v", err)
	}
	if len(got) != 0 {
		t.Fatalf("parseComposePSContainers() returned %d containers, want 0", len(got))
	}
}

func TestIsYesByte(t *testing.T) {
	for _, answer := range []byte{'y', 'Y'} {
		if !isYesByte(answer) {
			t.Fatalf("isYesByte(%q) = false, want true", answer)
		}
	}
	for _, answer := range []byte{0, '\n', 'n', 'N', 'd'} {
		if isYesByte(answer) {
			t.Fatalf("isYesByte(%q) = true, want false", answer)
		}
	}
}
