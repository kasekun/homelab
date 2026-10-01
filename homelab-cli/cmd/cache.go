package cmd

import (
	"encoding/json"
	"os"
	"path/filepath"
)

const cacheFileName = ".jdc-cache.json"

type jdcCache struct {
	Services []string `json:"services"`
	Profiles []string `json:"profiles"`
}

func cachePath(root string) string {
	return filepath.Join(root, cacheFileName)
}

// loadCache reads .jdc-cache.json from the repo root. Returns an empty cache
// (not an error) if the file does not exist, so completion degrades gracefully.
func loadCache(root string) (*jdcCache, error) {
	data, err := os.ReadFile(cachePath(root))
	if os.IsNotExist(err) {
		return &jdcCache{}, nil
	}
	if err != nil {
		return nil, err
	}
	var c jdcCache
	if err := json.Unmarshal(data, &c); err != nil {
		return nil, err
	}
	return &c, nil
}

// saveCache writes the cache to .jdc-cache.json at the repo root.
func saveCache(root string, c *jdcCache) error {
	data, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(cachePath(root), data, 0644)
}
