# Implementation ideas for every room

This is the "meta" cookbook which condenses the multiple features and tricks of [Magic Areas](https://github.com/jseidl/magic-areas) to magically and accurately (YMMV) track presence in every room of your house!

!!! warning
    Magic Areas strength is on stacking multiple somewhat-reliable sources of presence into a nice solid and reliable presence tracking system. You will likely need to use multiple sources of presence that will be good at one situation (static vs moving, for example) but bad at others until you cover all the situations. Magic Areas has features (such as "Keep-only sensors") that allow you to use even flappy or slow sensors.

## General considerations

### mmWave sensors

mmWave sensors are the absolute GOAT of human sensing. Some can be finicky to set up but once up and running they're reliable. mmWave sensors are not very good for exterior areas as there are lots of moving things, winds and animals. "Keep-only" functionality on Magic Areas allows us to bypass false-positives with curtains moving and animals but still might not be ideal.

!!! tip
    I recommend putting mmWave sensors in the "keep-only sensors" list and having a PIR motion sensor in the area alongside to avoid false-triggers.

### mmWave and PIR sensor positioning

Most presence sensors are able to sense the area in front of them, usually a cone shape with the tip being on the sensor, spreading out. This is called the sensor's field-of-view (FoV).

#### PIR sensors

PIR sensors are reliable and fast but they only detect movement, not people standing still. PIR's use infrared light (heat) and detect a change in that source's position across its FoV. It can't tell where you moved, which direction you moved, just that you moved.

!!! tip
    You should place them with their FoV towards the access of rooms, usually in the ceiling corner facing the area you walk through after you go through the door.

!!! failure
    Avoid placing looking directly at the door or it will trigger when you walk past the room.

#### mmWave sensors

These can be pointed wide in a corner as their FoV is usually wide and deep. You will need to tweak its settings until you're covering the room and not the other adjacent rooms as well. Prefer pointing mmWave sensors towards exterior walls rather than interior walls, when possible.

!!! note
    As you can see, PIR and mmWave have different positioning requirements and while PIR+mmWave combo sensors might be good for themselves on reducing false positives, they lose where their positioning is the same for both sensors. Magic Areas has the "keep-only sensors" functionality that will take care of reducing false-positives for you.

### Sensing presence on dumb devices

A quick and dirty way to detect a device being in use (and thus using this information to trigger presence) is to use a power-metering smart outlets. There are a plethora of those on the market for very little. Unless you need to actually control the outlet, you can find metering-only smart outlets (with no relay). These can be cheaper and you don't risk accidentally turning off the device.

Plug your device into the outlet, see how much it draws when in use, add a [Threshold sensor](https://www.home-assistant.io/integrations/threshold/) and set its device class to `presence` and add this entity to the area in question. Magic Areas will automatically pick it up and start using it as a presence source.

This is particularly useful for detecting workstation use through monitor power consumption, gym equipment use (e.g. treadmills), appliance use in the kitchen, knowing if an IR-controlled (not smart) light is actually on etc. Make sure the smart outlet is rated for the device you're plugging in! If you're plugging in anything with a motor or a heating element on it, do not skip this step.

### Wasp in a box

This is an interesting concept where when movement is detected on a room with closed doors, presence is inferred to be kept until a door is open. This is ideal for rooms where you usually close the door when you're in, like bathrooms (if you to pee with the doors open, then that isn't for you), bedrooms at bedtime, garages, laundry rooms etc. I will re-mention Wasp in a box on appropriate rooms below.

!!! warning
    Wasp in a box track [aggregates](../../features/aggregation.md) sensors and thus will consider ALL doors and motion sensors in an area.

### BLE Trackers

BLE trackers are excellent for keeping presence reliably but they have a slow initial detection and occasional "flapping" between areas. We recommend using BLE trackers as "keep only sensors".

This feature is designed to support most BLE tracker integrations such as [Bermuda](https://github.com/agittins/bermuda), [ESPresence](https://espresense.com/), [Room Assistant](https://www.room-assistant.io/) etc. I personally use Bermuda, but you do you.

!!! failure
    Tracking of BLE devices needs that you go "all in" and add BLE proxies/trackers to almost every room to avoid situations where you're in a room that doesn't have a tracker but it's next to a room that does have a tracker, thus marking you on the wrong room.

### Indoor cameras are creepy, but hear me out

If you can safely deploy cloudless/fully-local/isolated cameras, then I recommend using cameras on your interior common areas paired with [Frigate](https://frigate.video/) for person detection as a presence source.

### Sleep States

I use [Adaptive Lighting](https://github.com/basnijholt/adaptive-lighting) in all my rooms as most of my lights are at least dimmable. Adaptive Lighting provide a `switch` called "Sleep Mode" which is used by that integration to control your lights brightness and color in a different way.

Magic Areas can use those switches as "Sleep State" sensors. You can use any binary-state entity (`input_boolean`, `switch`, `binary_sensor`, etc) but it's very convenient to just reuse Adaptive Lighting's "Sleep Mode" switch. I like to make a `group` of switches with all the "Sleep Mode" switches from the common areas (basically everything that is not a bedroom) in the `all` mode. That way I can control the sleep state of all those areas at once via automations.

#### Automating sleep states

For common areas, I have a Template binary sensor called `night_mode` based off `sensor.time` that is `on` during the period of 00h00 until 08h00. I have an automation listening to changes in that binary sensor. You can totally just make the automation trigger on time directly but I use that sensor in other automations.

For each bedroom there's a different automation. My kid's room is triggered by her smart speaker playing after `sun.sun` is `below_horizon` (she sleeps with "sleep songs"). Master bedroom is triggered by the bed sensor detecting occupancy for over 10m and the TV is off. The guest bedroom is triggered by the `night_mode` sensor as well.


#### Sleep lights

I highly recommend having in every room possible a light source that is faint (or can be made faint) and small. These are great for when you're walking around the house in pitch black and you surely don't want bright lights being turned on by Magic Areas. Most ceiling lights will be either too bright at the minimum level or not even turn on when you dim them too low. It's best to use smaller lamps or decorative lights that can be run ~20-25% and give a good faint glow that is enough to light your path without hurting your eyes or disturbing nearby areas (for example, in the US, usually internal doors are required to have a significant gap behind them and light will leak from these gaps into the room).

### Timeouts and extended state

Magic Areas uses timeout settings to release the occupancy state of an area after not seeing any presence states for a while. These timeouts are configurable for regular occupancy, extended and sleep states. Extended state is gained after presence is held in an area after a configurable amount of time. This state can be used for light control but also overrides the regular timeout, allowing one to configure a longer timeout if an area has been occupied for this extended time.

!!! warning
    Fine-tuning those timeouts are **key** for consistent presence tracking. Prefer slower (bigger) timeouts and only pull back after you have more presence sources. Reliable presence sources such as mmWave, BLE Trackers or Wasp in a box might allow you to live with shorter "clear timeouts".

## Exterior

### Front Yard / Porch

The first thing to do is add a contact sensor to your front door. You may add this sensor to either your entry hall or the front yard / porch area, then force-add (using "include entities" option) to the other area. Use outdoor-rated motion sensors plus person-detection with your cameras (e.g. Frigate) if you happen to have it.

Motion sensors / person detection will be your initial trigger with the door holding presence while your stationary talking to someone at your door or putting the groceries / packages / mail in.

As your front door is susceptible to a lot of noisy movement sources, it might false trigger a LOT. In order to mitigate that you can try the following:
* Remove motion as source of presence
* Use outdoor-rated motion sensors that can be tuned to ignore smaller targets (animals)
* Use person-detection from Frigate, delineate a perimeter and exclude the sidewalk. This way you only will have triggers when someone crosses into your property.

### Backyard

Backyard will work similarly as the front yard but you can't rely on door sensors to keep presence up because one usually does not keep their backyard door open. You will need to rely either on person detection with cameras, add more motion sensors and play with "clear timeout" to be lax enough (~15m on extended mode should work).

On houses, you can split the backyard into three areas: one for the main backyard in the back of the house and one for each "side strips" (if you have it). This only makes sense if you have controllable lights on these "side strips". Then add the strips "area state tracker" sensor to the main backyard via "include entities".

!!! note
    We're putting those side strips in the backyard because they're usually behind the fence. If yours are not like this, feel free to play around.

## Interior

### Entry hall

One usually doesn't "hang out" in their entry hall unless they're talking to someone at the door. This make's the entry hall a similar candidate as the front yard / porch. Add the door (contact) sensor to keep presence and a motion sensor to trigger it initially. For the same reason, you can safely set a low "clear timeout" to maximize your energy savings (if using "light control").

### Living Room & Dining Room

These areas have the challenge of constantly having "standing still" occupancy while users are sitting down on the couch or at the table eating. This is a classic mmWave + PIR motion sensor scenario as power outlets are usually widely available on these areas. Person detection with indoor cameras can help but placing the cameras free of obstructions can be challenging. These areas have no doors (usually) so wasp-in-a-box is out of question. BLE trackers are particularly useful here as well.

Since those are high traffic (passing by) areas usually, be sure to set the "extended time" somewhat long (~5m) and the "extended timeout" also long, so the area has a "slow release" avoiding false-clears.

### Hallways

It depends on the kind of hallway. If your hallway is a passage only, meaning you'd rarely stand there for a while, then you might be able to get away with motion sensors and an appropriate "clear timeout". If you have closets, you may want to add contact sensors to the closet's doors.

### Family Room

Family room follows the same concept of living & dining room, except that you can use "watching the tv" as a presence source. This can be achieved the following ways:

* (if your TV is dumb -- not smart) Use a power-metering smart outlet, note the consumption with the TV off and with the TV on, add a Threshold sensor for when the TV is on, use that sensor as presence source on that area.
* (if your TV is smart) Use the media player state

BLE trackers are particularly useful here as well. Make sure to follow the "extended time" and "extended timeout" recommendations from Living Room & Dining Room above.

### Kitchen

Apart from the regular motion / mmWave sensors, kitchen can have a few more source of presence:

* (with a smart fridge) Use the door sensors of that device
* (with a dumb fridge) Add contact sensors to the doors
* (if your sink has a pull-out shower head) Strap a vibration sensor to the shower head hose under the sink. That baby slaps when water runs through it.
* (if you have a pantry) Use the pantry door sensor
* Use vibration sensors under your countertop as presence sources to catch when you're cutting stuff or placing dishes / glasses down.
* Use power-metering smart outlets with Threshold sensor to trigger presence when using appliances such as toaster, kettle etc.

If you don't have an mmWave sensor in the kitchen, you will need to play with the "extended time" and "extended timeout" to ensure consistent tracking.

### Pantry & Closets (and maybe Attics & small sheds)

These are areas where you don't usually close the door behind you, they have their doors closed when not in use and open while in use. A single door (contact) sensor should be enough to keep the area occupied while the door is open and clear when closed. This allows us to set "clear timeout" to 0 (zero) thus instantly releasing the occupancy state when the doors are closed.

!!! note
    It really only makes sense to create these "sub areas" for closets and pantries if you have lights (or other supported devices) to control automatically, otherwise you can add their door contact sensors directly to the parent area.

!!! warning
    Make sure to add the closet's area state tracker sensor to the area that holds the closet itself (e.g. bedroom, hallway) so their presence is kept while the closet is in use.

### Bathrooms

I've tried almost everything here. Motion sensors alone won't cut it, as you might already have some experience with it. Tracking humidity for baths works initially but either fails to keep tracking or fails to stop tracking. mmWave sensors are the absolute best option here but my peeve is that bathrooms don't usually benefit from well placed outlets.

mmWave sensors will usually "steal" one of your precious limited outlets, even thou battery-operated "sleeper" mmWave sensors exists, wired ones are more common. If you have a smart speaker there and only a 1-gang outlet, you're out of outlets for hair dryers and so. Also, usually the outlet isn't where the mmWave sensor would be better placed so likely you'll have a cord going unsightly.

Wasp in a box are very good at this, have a contact sensor at the door, a battery powered motion sensor at a corner and you should be OK. (for the most part).

!!! note
    mmWave are the best, if you can live with the issues described above, go for it. If not, wasp in a box is your friend!

!!! failure
    Don't add door sensors as presence sensors as those areas usually have doors open while unnocupied.

!!! warning
    "Clear timeout" setting for bathrooms is an artform and you will have to fiddle with it a bit as it will depend on your presence sources and how well they work. If wasp in a box is working reliable for you, you may be able to set a low "clear timeout".

!!! tip
    If you have an exhaust fan in your bathroom, you may want to use a humidity sensor paired with the [Fan Groups](../../features/fan-groups.md) feature tracking `humidity` of the area. This will automatically control your bathroom exhaust as needed.

### Bedrooms

Bedrooms also should have at least a PIR motion sensor and a mmWave sensor. BLE trackers are particularly useful here as well. You can get fancy and use "bed sensors", either off-the-shelf or DIY using load-cells/bathroom scales (just google it).

Wasp-in-a-box works well for bedrooms but only for bedtime when doors are actually closed (if you do close your doors on your bedrooms, of course). If you don't use wasp-in-a-box then setting a slow (~30m) "extended timeout" is recommended.

!!! warning
    If you have a suite bedroom, make sure to use the attached bathroom's area state tracker sensor as a presence sensor on the bedroom. This will help keep the bedroom occupied while you go to the bedroom in the middle of the night, otherwise your bedroom could go "clear" and when you walk back, the lights would turn on on you.

!!! tip
    If you have a TV on your bedroom, you can add it as a presence source the same way as in the Family Room.

!!! tip
    If you have fans in your bedroom, you can use [Fan Groups](../../features/fan-groups.md) to control them based off the area's temperature (you will need a temperature sensor in the area, evidently).

!!! tip
    On your own bedroom, you may get away from using an mmWave sensor if you have a BLE tracker and usually have your phone or smartwatch on you all the time.

### (Home) Offices

Areas that have computers on while in use can use this information for presence tracking. It's recommended that your computer is configure to auto-sleep after being idle for a while, in order to release presence. You can get this information from
* Ping sensor
* Integration with networking software (e.g. Unifi)
* Using a power-metering smart outlet to measure the consumption of your monitors. If you have more than one, use a T-splitter and connect all of them to the same metering outlet.

If you mostly use this are for using the computer, that alone + PIR motion sensor should do the trick. If you perform actions where you're sitting still but not on your computer (e.g. reading), you will need an mmWave sensor or a contact sensor with Wasp-in-abox (although you need to remember to close the door every time before reading). In this case you can set a pretty low "clear timeout".

!!! tip
    Using a vibration sensor on your chair can also work as source of presence, considering you have the habit of moving back and forth with the backrest or swinging your legs often.

### Garage (and bigger sheds)

Garages are usually cluttered spaces which hinders the ability of motion sensors (PIR) of working at their best by having a lot of blind spots. This can be countered by adding more motion sensors but this will result in more batteries for you to change. My garage has 3 accesses, the main garage door, a side door to the outside and a door to the inside of the house. I have contact sensors on all of those accesses and I use the `door` sensors as presence sensing. I have a camera doing person detection via Frigate, a single motion sensor up in a corner opposite to the camera and the Wasp-in-a-box feature turned on.

### Basement

Basements follow the same challenges as garages but it's not unusual to have the main access door open while you're down there so Wasp-in-a-box would not consistently help here. If you do usually close the door behind you (or it has auto-close), then Wasp-in-a-box will be useful. mmWave with a couple PIR motion sensors would be the best.

### Gym

If you use powered machines like treadmills, bikes, plug them into power-metering smart outlets and use a Threshold sensor to detect them being used. mmWave, Wasp-in-a-box and BLE trackers can also be used here. If you usually exercise with a smart speaker in the room, you can use this media player device as presence tracking as well.

## Meta-Areas

Meta-Areas are areas that are not Home Assistant areas but rather represent logical groups of areas. In Magic Areas, you can specify whether the area is an interior or exterior area. This allows 3 meta-areas to be created: One for all interior areas, one for all exterior areas and a "Global" meta-area for all areas.

This allows you to have things like:
* Average temperature of your home's interior. (and all other aggregates)
* Average illuminance of the exterior (to use as an "Area light sensor").
* Control all lights in a floor at the same time.

There are additional features that are exclusive to meta-areas such as the [Area-aware media player](../../features/area-aware-media-player.md) and features that are not exclusive to meta-areas but makes more sense in meta-areas such as [Climate control](../../features/climate-control.md).

### Exterior meta-area

I do recommend having illuminance sensors across your exterior areas for more accurate exterior luminance aggregation on the exterior meta-area.

### Floor meta-areas

I love those areas to tie my thermostat to the aggregate state of floors. Since I have a dual zone HVAC that exposes two climate entities to home assistant, I add [Climate control](../../features/climate-control.md) to each floor pointing to each climate device. If you have a single zone HVAC in a two story house, you can use the Interior meta-area instead.
