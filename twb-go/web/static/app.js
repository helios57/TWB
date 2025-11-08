window.onload = function() {
    var conn;
    var msg = document.getElementById("status");
    var villagesDiv = document.getElementById("villages");

    function connect() {
        if (window["WebSocket"]) {
            conn = new WebSocket("ws://" + document.location.host + "/ws");
            conn.onopen = function(evt) {
                msg.textContent = "Connected";
            }
            conn.onclose = function(evt) {
                msg.textContent = "Connection closed, reconnecting...";
                setTimeout(connect, 1000);
            };
            conn.onmessage = function(evt) {
                var data = JSON.parse(evt.data);
                render(data);
            };
            conn.onerror = function(evt) {
                msg.textContent = "Connection error";
            }
        } else {
            var item = document.createElement("div");
            item.innerHTML = "<b>Your browser does not support WebSockets.</b>";
            appendLog(item);
        }
    }
    connect();

    function formatLastAction(action) {
        if (!action) {
            return "None";
        }
        if (action.Building) {
            return `Build ${action.Building} (${action.Level})`;
        }
        if (action.Unit && action.Amount) {
            return `Recruit ${action.Amount} ${action.Unit}`;
        }
        if (action.Unit && action.Level) {
            return `Research ${action.Unit} (${action.Level})`;
        }
        if (action.Target) {
            return `Farm ${action.Target.ID}`;
        }
        return "Unknown";
    }

    function render(data) {
        villagesDiv.innerHTML = "";
        if (!data.Villages) {
            return;
        }
        for (var villageID in data.Villages) {
            var village = data.Villages[villageID];
            var villageEl = document.createElement("div");
            villageEl.className = "village";

            var title = document.createElement("h2");
            title.textContent = "Village " + villageID;
            villageEl.appendChild(title);

            var lastAction = document.createElement("p");
            lastAction.textContent = "Last Action: " + formatLastAction(village.LastAction);
            villageEl.appendChild(lastAction);

            var resources = document.createElement("p");
            resources.textContent = "Resources: Wood: " + village.Resources.Actual.Wood + ", Stone: " + village.Resources.Actual.Stone + ", Iron: " + village.Resources.Actual.Iron;
            villageEl.appendChild(resources);

            var buildingQueue = document.createElement("p");
            buildingQueue.textContent = "Building Queue: " + (village.BuildingQueue && village.BuildingQueue.length > 0 ? village.BuildingQueue.map(b => b.Building + " (" + b.Level + ")").join(", ") : "Empty");
            villageEl.appendChild(buildingQueue);

            var troopQueue = document.createElement("p");
            var troopQueueContent = "";
            if (village.TroopQueue) {
                for (var building in village.TroopQueue) {
                    var queue = village.TroopQueue[building];
                    if (queue.length > 0) {
                        troopQueueContent += building + ": " + queue.map(t => t.Unit + " (" + t.Count + ")").join(", ") + " ";
                    }
                }
            }
            troopQueue.textContent = "Troop Queue: " + (troopQueueContent || "Empty");
            villageEl.appendChild(troopQueue);

            villagesDiv.appendChild(villageEl);
        }
    }
};
