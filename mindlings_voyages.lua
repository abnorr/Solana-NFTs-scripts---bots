local discordia = require("discordia")
local json = require("json")
local http = require("coro-http")
local qs = require("querystring")
local timer = require("timer")

-- constants
local INTERVAL = 30
local SERVER_ID = "925295316348059729"
local VOYAGES_API = "https://a2-mind-prd-api.azurewebsites.net/api/utility/dashboard"

-- local LAMPORTS = 1000000000
local token = "YOUR DISCORD BOT TOKEN"

local function request(URL)

    local f = assert(io.open("input_voyages.txt", "w"))
    f:write(URL)
    f:close()

    os.execute("C:/Python310/python.exe requests_voyages.py")
    local res_file = assert(io.open("output_voyages.json", "r"))
    local content = res_file:read("*all")
    res_file.close()
    local res = json.decode(content)

    return res;

end

local function voyages()

    local res = request(VOYAGES_API)
	print (res)
    local totalMindlings = res
	local totalSpores = nil

	local i = 0
	local special_v = nil
	for k,v in pairs(res) do
		-- print(i)
		-- print(k,v)
		if i==0 then special_v = v; break
		end
		i = i + 1
	end
	local res2 = special_v
	for kk, vv in pairs(res2) do
		print(kk,vv)
	end
	totalMindlings = res2.totalMindlings
	totalSpores = res2.totalSpores

    return totalMindlings, totalSpores
end


local client = discordia.Client()
local server

local function update()

    local totalMindlings, totalSpores = voyages()


    server.me:setNickname(("Mindlings: %d"):format(totalMindlings))

    -- Set status
	client:setGame({
        name = ("Spores: %d"):format(totalSpores),
        type = 3
    })

end

client:on("ready", function()
    server = client:getGuild(SERVER_ID)

    update()

    timer.setInterval(INTERVAL * 1000, function()
        coroutine.wrap(update)()
    end)
end)

client:run("Bot "..token)
