# Smart community 4.2 m scene

This is a planned 4.2 x 4.2 m Gazebo layout built from the rules schematic and
the 9.24 training PDF. The official picture defines topology and orientations
but has no dimensioned prop anchors. All exact prop coordinates and observation
points are documented as engineering placements in `docs/scene_manifest_4p2.json`.

Run `python3 tools/gen_scene_4p2.py` to regenerate the world, manifest, SVG
plan, task point CSV, config and one reusable traffic signal model. Run
`python3 tools/verify_scene_4p2.py` for XML, asset, coordinate and road
connectivity checks. The 21 x 21 logical grid has 0.2 m cells; a cell center
`(x,y)` maps to Gazebo `(-2.0+0.2*x,-2.0+0.2*y)`. The six connected road strips
are each 0.6 m wide. The start/finish is the 0.6 m upper-right region, centered
at `(1.8,1.8)` Gazebo metres.

`python3 tools/gen_route_4p2.py` creates
`route/sq_route_patrol_4p2.csv` from the 16 task points. It contains 17
additional centre-line transit goals (33 goals total) and is readable by the
new `sq_patrol_4p2.py` controller. It is a geometric plan only. Do not run it with
the old `sq_navigation.launch` map or assume the old planner footprint,
traffic-light handling or vision result logic applies to the 4.2 m field.

`python3 tools/gen_map_4p2.py` rasterizes this world's collision geometry to
`maps/sq_community_4p2.pgm`; `python3 tools/verify_map_4p2.py` checks the map
and the 334 x 303 mm body at all planned route goals. `sq_navigation_4p2.launch` loads
that map and separate mecanum costmap/DWA parameters. The PGM is a geometric
prior, not a SLAM map. The 33-goal odometry/LiDAR patrol has been run in
Gazebo with the revised mecanum robot; its acceptance results are recorded
separately. AMCL and move_base have been started for live sensor checking,
but the 33-goal run does not use their plans.

`roslaunch sq_community sq_community_4p2.launch` starts the planned
world, a 334 x 303 x 222 mm four-mecanum-wheel body and two 10/15/3 second
signals. The robot dimensions and 34 mm chassis clearance come from the
MO-SERGEANT experimental guide. Four opposing 45-degree roller wheels are
modelled; Gazebo's planar-motion plugin approximates holonomic mecanum
kinematics and publishes `odom`. This is a kinematic simulation, not a
roller-contact dynamics model. One 360-degree laser, one RGB/depth camera and
one wide monocular task camera publish on `/scan`, `/camera/*` and
`/task_camera/image_raw`. The monocular camera frames tall buildings and
roadside task props. The training PDF recommends
yellow 5 s while the formal rules say yellow 3 s; this scene uses 3 s.
The expanded URDF visual envelope has been measured at 334 x 303 x 222 mm;
the side guards set the 303 mm width and the chassis bottom is 34 mm above
the ground.

For a one-command demonstration, run
`roslaunch sq_community sq_autonomous_4p2.launch`. This starts the world,
navigation processes, a front-camera traffic-signal classifier and the 33-goal
patrol. The patrol uses odometry, LiDAR and camera frames; signal crossings
wait for an observed red-to-green transition. Task-point JPEGs and a JSON
route report are written under `/tmp/sq4_patrol_frames` and
`/tmp/sq4_patrol_4p2.json`. The snapshots are evidence frames; the three
car tasks are recognized when the OCR worker is running, while people and fire
recognition await the separately supplied YOLO program. The patrol is a surveyed route
controller, not a general SLAM or autonomous exploration solution.
The front RGBD camera saves the people, car plate, gauge and signal views;
the rear-mounted wide monocular camera saves whole-building and area views.

For an optional offline plate check on the three captured car JPEGs, run
`python3 tools/plate_ocr_4p2.py <CAR_1.jpg> <CAR_2.jpg> <CAR_3.jpg> --output plates.json`
in a Python 3 environment with OpenCV and EasyOCR installed. This uses image
color and OCR, with a separate D/F character read on green new-energy plates.
It was checked against the three Gazebo patrol images. It has not yet been
tested on unknown plates.

The live OCR path is now connected to the patrol's three `CAR_*` observation
events. On the Windows host, start the persistent Python 3 worker with
`python3 tools/plate_ocr_server_4p2.py --host 192.168.232.1 --port 8765`.
The tested Anaconda installation requires `KMP_DUPLICATE_LIB_OK=TRUE` in that
process environment because it loads two OpenMP runtimes. The VM's ROS Melodic
Python 2 node `sq_plate_ocr_bridge_4p2.py` sends each captured JPEG to that
worker and publishes JSON on `/sq/vision/plate`; it writes
`/tmp/sq4_plate_results.jsonl`. The OCR URL is configurable with the launch
argument `ocr_url`. The worker must be reachable when the patrol runs; the VM
does not currently have EasyOCR installed. `sq_voice_4p2.py` speaks car results
and the camera-recognized red/yellow/green decisions using Speech Dispatcher,
and retains the last sentence on `/sq/voice/last`. The three known patrol JPEGs
passed a full VM-to-host-to-VM OCR smoke test. This is an integration check,
not a generalization test.

`sq_task_plan_4p2.py` fixes the 16 observation task IDs and their recognition
types in program code. `route/sq_route_patrol_4p2.csv` supplies their surveyed
map-frame coordinates and 17 transit goals. Each captured task publishes
`/sq/patrol/observation` JSON with `task_id`, `task_type`, `image`, and `stamp`;
the future YOLO worker can use this same event contract.

For actual SLAM and move_base work, `sq_gmapping_4p2.launch` configures
GMapping for this field. `sq_mapping_run_4p2.launch` starts the scene, GMapping,
signal vision, speech, and the guarded odometry patrol; after completing the
mapping route, save `/map` using `rosrun map_server map_saver -f
$(find sq_community)/maps/sq_slam_4p2`. The mapping launch must not run with
AMCL/map_server. `sq_autonomous_nav_4p2.launch` starts a separate
`move_base` action patrol over the same 33 goals and accepts
`map_file:=$(find sq_community)/maps/sq_slam_4p2.yaml` once a verified SLAM
map is available. Its traffic-light wait and OCR events are preserved. Never
start `sq_patrol_4p2.py` and `sq_patrol_nav_4p2.py` together, because both
would control `/cmd_vel`. The old 10 x 7.2 m map and coordinates are not valid
for the new field; these new SLAM and action-patrol paths require live acceptance
results before they can be called complete.

The two signals each have one housing with three photo-material panels.
The controller moves inactive panels into the opaque housing rather than
parking spare models below the floor. Building front, side and rear facades
use aligned three-storey window grids; A/B/C fire windows and D's second-floor
hot window remain individual task targets.

The launch opens Gazebo GUI by default and gives both Gazebo processes the
package's `models` directory via `GAZEBO_MODEL_PATH`. For a headless run,
pass `gui:=false`. If attaching a separate `gzclient` to an already running
headless server, export the same model path before starting that client:

```bash
export GAZEBO_MODEL_PATH=/home/terry/sq_ws/src/sq_community/models:${GAZEBO_MODEL_PATH:-}
gzclient
```

Without the model path in the graphical client, the models exist in the world
but their photo materials appear as plain grey or white panels.

Retained reference assets include 18 distinct page 5 standee textures (16 residents
and two non-residents). The default world uses independent training-reference standees; see the
2026-10-02 section below. Other assets include the user's three light photos and one transparent
rear-car cutout, a large-passenger rear cutout and separate exact-text plates.
Blue (small passenger), yellow (large passenger) and green (small pure electric)
plates occupy the three schematic car bays. The white police plate is packaged
for exchange, not deployed as a fourth bay. Run `python3 tools/gen_plates_4p2.py`
to regenerate the four plate PNGs and metadata; a CJK font and Pillow are
required. Each plate standee remains 95 x 30 x 0.1 mm as specified in the
training PDF, and each vehicle-rear standee is 345 x 250 x 0.5 mm. Earlier generic building, fire, gauge,
bin and sign textures are used as task proxies, without old coordinates.

The old `sq_community.world`, maps, routes and navigation parameters remain
untouched. A new SLAM map and mecanum navigation tuning need live
Gazebo mapping and are not implied by static scene generation. The 4.2 m
AMCL launch overrides TurtleBot3's differential odometry model to omni and
uses a tighter initial pose covariance; the costmap inflation radius is
0.17 m and DWA lateral speed is limited to 0.03 m/s for lane keeping.

## 2026-10-02 correction: training-reference person standees

The formal default `worlds/sq_community_4p2.world` contains 18 independent
person standees using the existing training-page-5 portrait textures. Each
visual envelope and collision box measures **150 mm high, 50 mm wide, 5 mm
thick**. A white backing and a printed layer share one static model per person.
There are 16 resident references and two outsider references (06 and 16), with
nine people in each street zone. This A/B split is an engineered arrangement,
not a mandatory example count. Positions are staggered; printed faces point
toward the northern observation roads. Identity metadata is not a detector output.

The previous volumetric cartoon people were an assistant interpretation that
did not satisfy the training specification. They are superseded and are no
longer loaded by the default world or generated by the default build. Original
files remain for recovery. `sq_community_4p2_standees.world` is now an identical
compatibility alias; ordinary launches already use the correct representation.

Training p5 explicitly says 50 mm width, while the p19 editing demonstration
uses 40 mm. This project follows the explicit p5 size requirement. The texture
layer is included within the total 5 mm thickness. The existing source portrait
images have not been redrawn or replaced with different characters.

The electric moped models are unchanged by this correction. Their 180 x 75 x
130 mm dimensions are engineering choices, not official specified dimensions.
The parking area contains eight upright and two fallen mopeds; A has two
illegal-parking examples. These are demonstration counts, not fixed competition
requirements. See the current Chinese acceptance report below for limitations.

After `python3 tools/gen_scene_4p2.py`, run:

```bash
python3 tools/verify_scene_4p2.py
python3 tools/verify_props_3d.py
python3 tools/gen_props_views_4p2.py
```

Despite its historical filename, `verify_props_3d.py` now checks the default
standee visual/collision dimensions, original texture assignments, independent
IDs, ground placement, zone containment and pairwise prop separation, together
with the existing moped geometry. Its JSON output retains the existing filename
`docs/props_3d_validation.json` for compatibility.

`config/props_observation_views_4p2.json` contains 14 suggested front-camera
QA poses, including an A-zone shifted pose to avoid the signal pole. These
poses have NOT been integrated into patrol. Geometric framing checks do not
prove recognition accuracy or absence of all occlusions. QA capture temporarily
sets robot poses through Gazebo services and restores the starting pose; it
is not an autonomous navigation test.

Current report: `docs/人物立牌纠正验收_20261002.md`.
Current images: `docs/standee_review_20261002/`.
The earlier `docs/props_3d_review_20261002/` images are superseded history.
