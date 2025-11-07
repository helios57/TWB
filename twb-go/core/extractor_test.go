package core

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

const mockGameStateHTML = `
<script>
TribalWars.updateGameData({
    "village": {
        "id": 1,
        "name": "Test Village",
        "wood": 100.5,
        "stone": 200.2,
        "iron": 300.8,
        "pop": 50,
        "pop_max": 100,
        "storage_max": 1000,
        "buildings": {
            "main": "1",
            "barracks": "1"
        }
    }
});
</script>
`

const mockUnitsInVillageHTML = `
<table id="units_home">
    <tr><td></td></tr>
    <tr>
        <td class="unit-item unit-item-spear">10</td>
        <td class="unit-item unit-item-sword">20</td>
    </tr>
</table>
`

const mockVillageIDsHTML = `
<div>
    <a class="menu_row2_village" href="game.php?village=123&screen=overview">Village 1</a>
    <a class="menu_row2_village" href="game.php?village=456&screen=overview">Village 2</a>
</div>
`

const mockBuildingCostsHTML = `
<table id="building_main">
    <tr class="row_a">
        <td><a href="#">main   (Level 1)</a></td>
        <td><span class="cost_wood">10</span> <span class="cost_stone">20</span> <span class="cost_iron">30</span> <span class="cost_pop">5</span></td>
        <td><a href="build_link_main">Build</a></td>
    </tr>
    <tr class="row_b">
        <td><a href="#">barracks   (Level 1)</a></td>
        <td><span class="cost_wood">15</span> <span class="cost_stone">25</span> <span class="cost_iron">35</span> <span class="cost_pop">10</span></td>
        <td></td>
    </tr>
</table>
`

const mockRecruitDataHTML = `
<form id="train_form">
    <table>
        <tbody>
            <tr class="row_a">
                <td><input name="spear" class="unitsInput" /></td>
                <td><span class="cost_wood">5</span> <span class="cost_stone">10</span> <span class="cost_iron">15</span> <span class="cost_pop">1</span></td>
                <td><a class="btn-recruit">Recruit</a></td>
            </tr>
        </tbody>
    </table>
</form>
`

const mockHTokenHTML = `
<input type="hidden" name="h" value="mock_h_token" />
`

const mockBuildingQueueHTML = `
<table id="build_queue">
    <tr class="build_order">
        <td>Headquarters (Stufe 1)</td>
        <td><span class="timer" data-duration="10">0:00:10</span></td>
        <td><a href="game.php?village=1&screen=main&action=cancel&id=1&h=abc" class="btn btn-cancel">cancel</a></td>
    </tr>
    <tr class="build_order">
        <td>Barracks (Stufe 2)</td>
        <td><span class="timer" data-duration="20">0:00:20</span></td>
        <td><a href="game.php?village=1&screen=main&action=cancel&id=2&h=def" class="btn btn-cancel">cancel</a></td>
    </tr>
</table>
`

const mockRecruitQueuesHTML = `
<div class="unit_queue_wrapper">
    <a class="building_title" href="game.php?screen=barracks">Barracks</a>
    <table class="trainqueue_wrap">
        <tr>
            <td>1 Spear Fighter</td>
            <td><span class="timer" data-duration="5">0:00:05</span></td>
            <td><a href="game.php?village=1&screen=barracks&action=cancel&id=3&h=ghi" class="btn btn-cancel">cancel</a></td>
        </tr>
    </table>
</div>
<div class="unit_queue_wrapper">
    <a class="building_title" href="game.php?screen=stable">Stable</a>
    <table class="trainqueue_wrap">
        <tr>
            <td>2 Light Cavalry</td>
            <td><span class="timer" data-duration="15">0:00:15</span></td>
            <td><a href="game.php?village=1&screen=stable&action=cancel&id=4&h=jkl" class="btn btn-cancel">cancel</a></td>
        </tr>
		<tr>
            <td>3 Light Cavalry</td>
            <td><span class="timer" data-duration="15">0:00:15</span></td>
            <td><a href="game.php?village=1&screen=stable&action=cancel&id=5&h=mno" class="btn btn-cancel">cancel</a></td>
        </tr>
    </table>
</div>
`

func TestExtractor_GameState(t *testing.T) {
	gs, err := Extractor.GameState(mockGameStateHTML)
	assert.NoError(t, err)
	assert.NotNil(t, gs)
	assert.Equal(t, 1, gs.Village.ID)
	assert.Equal(t, "Test Village", gs.Village.Name)
	assert.Equal(t, 100.5, gs.Village.Wood)
	assert.Equal(t, "1", gs.Village.Buildings["main"])
}

func TestExtractor_UnitsInVillage(t *testing.T) {
	units, err := Extractor.UnitsInVillage(mockUnitsInVillageHTML)
	assert.NoError(t, err)
	assert.Len(t, units, 2)
	assert.Equal(t, 10, units["spear"])
	assert.Equal(t, 20, units["sword"])
}

func TestExtractor_VillageIDs(t *testing.T) {
	ids, err := Extractor.VillageIDs(mockVillageIDsHTML)
	assert.NoError(t, err)
	assert.Len(t, ids, 2)
	assert.Equal(t, "123", ids[0])
	assert.Equal(t, "456", ids[1])
}

func TestExtractor_BuildingCosts(t *testing.T) {
	costs, err := Extractor.BuildingCosts(mockBuildingCostsHTML)
	assert.NoError(t, err)
	assert.Len(t, costs, 2)
	mainCost := costs["main"]
	assert.Equal(t, 10, mainCost.Wood)
	assert.True(t, mainCost.CanBuild)
	assert.Equal(t, "build_link_main", mainCost.BuildLink)
	barracksCost := costs["barracks"]
	assert.Equal(t, 15, barracksCost.Wood)
	assert.False(t, barracksCost.CanBuild)
}

func TestExtractor_RecruitData(t *testing.T) {
	data, err := Extractor.RecruitData(mockRecruitDataHTML)
	assert.NoError(t, err)
	assert.Len(t, data, 1)
	spearData := data["spear"]
	assert.Equal(t, 5, spearData.Wood)
	assert.True(t, spearData.RequirementsMet)
}

func TestExtractor_HToken(t *testing.T) {
	token, err := Extractor.HToken(mockHTokenHTML)
	assert.NoError(t, err)
	assert.Equal(t, "mock_h_token", token)
}

func TestExtractor_BuildingQueue(t *testing.T) {
	queue, err := Extractor.BuildingQueue(mockBuildingQueueHTML)
	assert.NoError(t, err)
	assert.Len(t, queue, 2)

	assert.Equal(t, "1", queue[0].ID)
	assert.Equal(t, "Headquarters", queue[0].Building)
	assert.Equal(t, 1, queue[0].Level)
	assert.Equal(t, 10*time.Second, queue[0].Duration)

	assert.Equal(t, "2", queue[1].ID)
	assert.Equal(t, "Barracks", queue[1].Building)
	assert.Equal(t, 2, queue[1].Level)
	assert.Equal(t, 20*time.Second, queue[1].Duration)
}

func TestExtractor_RecruitQueues(t *testing.T) {
	queues, err := Extractor.RecruitQueues(mockRecruitQueuesHTML)
	assert.NoError(t, err)
	assert.Len(t, queues, 2)

	assert.Contains(t, queues, "barracks")
	barracksQueue := queues["barracks"]
	assert.Len(t, barracksQueue, 1)
	assert.Equal(t, "3", barracksQueue[0].ID)
	assert.Equal(t, "Spear Fighter", barracksQueue[0].Unit)
	assert.Equal(t, 1, barracksQueue[0].Count)
	assert.Equal(t, 5*time.Second, barracksQueue[0].Duration)

	assert.Contains(t, queues, "stable")
	stableQueue := queues["stable"]
	assert.Len(t, stableQueue, 2)

	assert.Equal(t, "4", stableQueue[0].ID)
	assert.Equal(t, "Light Cavalry", stableQueue[0].Unit)
	assert.Equal(t, 2, stableQueue[0].Count)
	assert.Equal(t, 15*time.Second, stableQueue[0].Duration)

	assert.Equal(t, "5", stableQueue[1].ID)
	assert.Equal(t, "Light Cavalry", stableQueue[1].Unit)
	assert.Equal(t, 3, stableQueue[1].Count)
	assert.Equal(t, 15*time.Second, stableQueue[1].Duration)
}
