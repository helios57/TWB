package core

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
)

// BuildingCost represents the resource cost of a building.
type BuildingCost struct {
	Wood      int
	Stone     int
	Iron      int
	Pop       int
	CanBuild  bool
	BuildLink string
}

// BuildingUpgrade represents the data for a single level of a building.
type BuildingUpgrade struct {
	Level      int            `yaml:"level"`
	Resources  map[string]int `yaml:"resources"`
	Population int            `yaml:"population"`
	Storage    int            `yaml:"storage"`
	Production map[string]int `yaml:"production"`
	BuildTime  int            `yaml:"build_time"`
}

// BuildingData represents the static data for a building type.
type BuildingData struct {
	MaxLevel int               `yaml:"max_level"`
	Upgrades []BuildingUpgrade `yaml:"upgrades"`
}

// UnitData represents the static data for a unit type.
type UnitData struct {
	Prerequisites  map[string]int `yaml:"prerequisites"`
	Resources      map[string]int `yaml:"resources"`
	BuildTime      int            `yaml:"build_time"`
	Population     int            `yaml:"population"`
	Speed          int            `yaml:"speed"`
	Loot           int            `yaml:"loot"`
	Attack         int            `yaml:"attack"`
	Defense        int            `yaml:"defense"`
	DefenseCavalry int            `yaml:"defense_cavalry"`
	DefenseArcher  int            `yaml:"defense_archer"`
}

// ResearchUpgrade represents the data for a single level of research.
type ResearchUpgrade struct {
	Level        int            `yaml:"level"`
	Resources    map[string]int `yaml:"resources"`
	ResearchTime int            `yaml:"research_time"`
}

// ResearchData represents the static research data for a unit type.
type ResearchData struct {
	MaxLevel int               `yaml:"max_level"`
	Upgrades []ResearchUpgrade `yaml:"upgrades"`
}

// QueueItem represents an item in a building or recruitment queue.
type QueueItem struct {
	ID        string
	Building  string
	Unit      string
	Level     int
	Count     int
	Duration  time.Duration
	Completes time.Time
}

// GameState represents the game data.
type GameState struct {
	Village struct {
		ID         int               `json:"id"`
		Name       string            `json:"name"`
		Wood       float64           `json:"wood"`
		Stone      float64           `json:"stone"`
		Iron       float64           `json:"iron"`
		Pop        int               `json:"pop"`
		PopMax     int               `json:"pop_max"`
		StorageMax int               `json:"storage_max"`
		Buildings  map[string]string `json:"buildings"`
	} `json:"village"`
	BuildingQueue []QueueItem
	RecruitQueues map[string][]QueueItem
}

// Extractor provides methods for parsing HTML.
var Extractor = &extractor{}

// UnitCost represents the resource cost of a unit.
type UnitCost struct {
	Wood            int
	Stone           int
	Iron            int
	Pop             int
	RequirementsMet bool
}

type extractor struct{}

// GameState extracts the game state from the HTML.
func (e *extractor) GameState(html string) (*GameState, error) {
	re := regexp.MustCompile(`(?s)TribalWars\.updateGameData\((.+?)\);`)
	matches := re.FindStringSubmatch(html)
	if len(matches) < 2 {
		return nil, fmt.Errorf("game data not found in HTML")
	}

	var gameState GameState
	err := json.Unmarshal([]byte(matches[1]), &gameState)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal game data: %w", err)
	}

	return &gameState, nil
}

// UnitsInVillage extracts the units in the village from the HTML.
func (e *extractor) UnitsInVillage(html string) (map[string]int, error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to create goquery document: %w", err)
	}

	units := make(map[string]int)
	doc.Find("#units_home tr").Each(func(i int, s *goquery.Selection) {
		if i == 1 {
			s.Find("td.unit-item").Each(func(j int, s *goquery.Selection) {
				class, _ := s.Attr("class")
				parts := strings.Split(class, " ")
				unit := strings.TrimPrefix(parts[1], "unit-item-")
				count, _ := strconv.Atoi(s.Text())
				units[unit] = count
			})
		}
	})

	return units, nil
}

// VillageIDs extracts the village IDs from the HTML.
func (e *extractor) VillageIDs(html string) ([]string, error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to create goquery document: %w", err)
	}

	var villageIDs []string
	villageIDMap := make(map[string]bool)
	doc.Find("a[href*='village=']").Each(func(i int, s *goquery.Selection) {
		href, _ := s.Attr("href")
		re := regexp.MustCompile(`village=(\d+)`)
		matches := re.FindStringSubmatch(href)
		if len(matches) > 1 {
			if _, ok := villageIDMap[matches[1]]; !ok {
				villageIDs = append(villageIDs, matches[1])
				villageIDMap[matches[1]] = true
			}
		}
	})

	return villageIDs, nil
}

// BuildingCosts extracts the building costs from the HTML.
func (e *extractor) BuildingCosts(html string) (map[string]BuildingCost, error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to create goquery document: %w", err)
	}

	costs := make(map[string]BuildingCost)
	doc.Find("#building_main tr.row_a, #building_main tr.row_b").Each(func(i int, s *goquery.Selection) {
		buildingNode := s.Find("td:first-child a")
		buildingNameRaw := strings.TrimSpace(buildingNode.Text())
		re := regexp.MustCompile(`\s\s+`)
		buildingNameClean := re.ReplaceAllString(buildingNameRaw, " ")
		re = regexp.MustCompile(`^([a-zA-Z_]+)`)
		buildingMatch := re.FindStringSubmatch(buildingNameClean)
		if len(buildingMatch) < 2 {
			return
		}
		building := strings.ToLower(buildingMatch[1])

		var cost BuildingCost
		s.Find("span.cost_wood, span.cost_stone, span.cost_iron, span.cost_pop").Each(func(j int, s *goquery.Selection) {
			val, _ := strconv.Atoi(s.Text())
			if s.HasClass("cost_wood") {
				cost.Wood = val
			} else if s.HasClass("cost_stone") {
				cost.Stone = val
			} else if s.HasClass("cost_iron") {
				cost.Iron = val
			} else if s.HasClass("cost_pop") {
				cost.Pop = val
			}
		})

		buildLink, exists := s.Find("td:last-child a").Attr("href")
		cost.CanBuild = exists
		if exists {
			cost.BuildLink = buildLink
		}

		costs[building] = cost
	})

	return costs, nil
}

// RecruitData extracts the recruitment data from the HTML of a training building.
func (e *extractor) RecruitData(html string) (map[string]UnitCost, error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to create goquery document: %w", err)
	}

	data := make(map[string]UnitCost)
	doc.Find("form#train_form tr.row_a, form#train_form tr.row_b").Each(func(i int, s *goquery.Selection) {
		unitName, exists := s.Find("input.unitsInput").Attr("name")
		if !exists {
			return
		}

		var cost UnitCost
		s.Find("span.cost_wood, span.cost_stone, span.cost_iron, span.cost_pop").Each(func(j int, s *goquery.Selection) {
			val, _ := strconv.Atoi(s.Text())
			if s.HasClass("cost_wood") {
				cost.Wood = val
			} else if s.HasClass("cost_stone") {
				cost.Stone = val
			} else if s.HasClass("cost_iron") {
				cost.Iron = val
			} else if s.HasClass("cost_pop") {
				cost.Pop = val
			}
		})

		cost.RequirementsMet = s.Find("a.btn-recruit").Length() > 0
		data[unitName] = cost
	})

	return data, nil
}

// BuildingQueue extracts the building queue from the HTML.
func (e *extractor) BuildingQueue(html string) ([]QueueItem, error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to create goquery document: %w", err)
	}

	var queue []QueueItem
	doc.Find("table#build_queue tr.build_order").Each(func(i int, s *goquery.Selection) {
		var item QueueItem
		buildingAndLevel := strings.TrimSpace(s.Find("td:first-child").Text())
		re := regexp.MustCompile(`(.+)\s+\(Stufe (\d+)\)`)
		matches := re.FindStringSubmatch(buildingAndLevel)
		if len(matches) == 3 {
			var err error
			item.Building = matches[1]
			item.Level, err = strconv.Atoi(matches[2])
			if err != nil {
				item.Level = 0
			}
		} else {
			item.Building = buildingAndLevel
		}

		durationStr, _ := s.Find("span.timer").Attr("data-duration")
		duration, _ := strconv.Atoi(durationStr)
		item.Duration = time.Duration(duration) * time.Second
		item.Completes = time.Now().Add(item.Duration)

		cancelLink, _ := s.Find("a.btn-cancel").Attr("href")
		idRe := regexp.MustCompile(`id=(\d+)`)
		idMatches := idRe.FindStringSubmatch(cancelLink)
		if len(idMatches) > 1 {
			item.ID = idMatches[1]
		}

		queue = append(queue, item)
	})

	return queue, nil
}

// RecruitQueues extracts the recruitment queues from the HTML.
func (e *extractor) RecruitQueues(html string) (map[string][]QueueItem, error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to create goquery document: %w", err)
	}

	queues := make(map[string][]QueueItem)
	doc.Find("div.unit_queue_wrapper").Each(func(i int, s *goquery.Selection) {
		building, _ := s.Find("a.building_title").Attr("href")
		building = strings.TrimPrefix(building, "game.php?screen=")
		re := regexp.MustCompile(`^([a-z_]+)`)
		matches := re.FindStringSubmatch(building)
		if len(matches) < 2 {
			return
		}
		building = matches[1]

		var queue []QueueItem
		s.Find("table.trainqueue_wrap tr").Each(func(j int, s *goquery.Selection) {
			if s.Find("a.btn-cancel").Length() == 0 {
				return
			}
			var item QueueItem
			countAndUnit := strings.TrimSpace(s.Find("td:first-child").Text())
			parts := strings.SplitN(countAndUnit, " ", 2)
			var err error
			item.Count, err = strconv.Atoi(parts[0])
			if err != nil {
				item.Count = 0
			}
			item.Unit = strings.TrimSpace(parts[1])

			durationStr, _ := s.Find("span.timer").Attr("data-duration")
			duration, err := strconv.Atoi(durationStr)
			if err != nil {
				duration = 0
			}
			item.Duration = time.Duration(duration) * time.Second
			item.Completes = time.Now().Add(item.Duration)

			cancelLink, _ := s.Find("a.btn-cancel").Attr("href")
			idRe := regexp.MustCompile(`id=(\d+)`)
			idMatches := idRe.FindStringSubmatch(cancelLink)
			if len(idMatches) > 1 {
				item.ID = idMatches[1]
			}
			queue = append(queue, item)
		})
		queues[building] = queue
	})

	return queues, nil
}

// HToken extracts the h token from the HTML.
func (e *extractor) HToken(html string) (string, error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return "", fmt.Errorf("failed to create goquery document: %w", err)
	}

	h, exists := doc.Find("input[name=h]").Attr("value")
	if !exists {
		return "", fmt.Errorf("h token not found")
	}

	return h, nil
}

// ResearchLevels extracts the research levels from the HTML of the smithy.
func (e *extractor) ResearchLevels(html string) (map[string]int, error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to create goquery document: %w", err)
	}

	levels := make(map[string]int)
	doc.Find("table.vis tr[class*='row_']").Each(func(i int, s *goquery.Selection) {
		unitNode := s.Find("td:first-child a")
		if unitNode.Length() == 0 {
			return
		}

		href, _ := unitNode.Attr("href")
		re := regexp.MustCompile(`tech=([a-z_]+)`)
		matches := re.FindStringSubmatch(href)
		if len(matches) < 2 {
			return
		}
		unit := matches[1]

		levelStr := strings.TrimSpace(s.Find("td:nth-child(2)").Text())
		level, err := strconv.Atoi(levelStr)
		if err != nil {
			level = 0
		}
		levels[unit] = level
	})

	return levels, nil
}
