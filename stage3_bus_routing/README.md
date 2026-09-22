Here is the complete extracted `README.md` file in Markdown format, combined from all provided images:

# Stage 3: School Bus Routing (Capacitated Vehicle Routing)



**Question.** Ten bus stops with 58 students total, three buses with 24 seats each. Which stops does each bus serve, and in what order, to minimize total distance?

**Answer.** The nearest-neighbor rule a dispatcher would use drives 40.1 km. The integer program drives 36.1 km, 10% less, with better balanced loads, and proves no plan is shorter.

Left: nearest neighbor sends bus 2 on a long loop because it greedily grabbed the closest stop each time and left Meadow Dr (stop 10) stranded. Right: the optimizer divides the map into three clean wedges.

## The model



This is the two-index formulation of the Capacitated Vehicle Routing Problem (CVRP) with Miller-Tucker-Zemlin (MTZ) load constraints.

**Index sets**

* $N = \{1, \dots, 10\}$ bus stops


* $V = N \cup \{0\}$ where 0 is the school (the depot)



**Data**

* $d_{ij}$: distance from $i$ to $j$ (Euclidean, from coordinates in `data/stops.csv`)


* $q_j$: students waiting at stop $j$

* $K = 3$ buses, $Q = 24$ seats each (`data/config.json`)



**Decision variables**

$$x_{ij} \in \{0,1\} \quad \text{a bus drives directly from } i \text{ to } j \quad (i \ne j)$$

$$u_j \in [q_j, Q] \quad \text{students on board just after picking up stop } j$$

**Objective**[cite: 1, 2]

$$\min \sum_{i \ne j} d_{ij} x_{ij}$$


[cite: 1, 2]

**Constraints**[cite: 2]

$$\text{(1) arrive once: } \sum_{i \in V, i \ne j} x_{ij} = 1 \quad \forall j \in N$$


[cite: 2]


$$\text{(2) leave once: } \sum_{j \in V, j \ne i} x_{ij} = 1 \quad \forall i \in N$$


[cite: 2]


$$\text{(3) bus limit: } \sum_{j \in N} x_{0j} \le K$$


[cite: 2]


$$\text{(4) MTZ load: } u_j \ge u_i + q_j - Q(1 - x_{ij}) \quad \forall i, j \in N, i \ne j$$


[cite: 2]


$$\text{(5) load bounds: } q_j \le u_j \le Q \quad \forall j \in N$$


[cite: 2]

## Why constraint (4) is the whole trick[cite: 2]

Constraints (1) and (2) alone say every stop has one bus arriving and one leaving.[cite: 2] That is satisfied by a route that never visits the school at all: a closed loop 1 -> 2 -> 3 -> 1 is perfectly legal under (1) and (2).[cite: 2] These disconnected loops are called **sub-tours**, and eliminating them is the hard part of every routing problem.[cite: 2]

Look at (4) in its two cases:[cite: 2]

* If $x_{ij} = 0$: the constraint reads $u_j \ge u_i + q_j - Q$. Since $u_i \le Q$, the right side is at most $q_j$, and $u_j \ge q_j$ already. **No effect.**[cite: 2]
* If $x_{ij} = 1$: the constraint reads $u_j \ge u_i + q_j$. **The load strictly increases** by at least $q_j$ every time the bus moves to a new stop.[cite: 2]

Now suppose a sub-tour 1 -> 2 -> 3 -> 1 existed.[cite: 2] Following (4) around the loop: $u_2 \ge u_1 + q_2$, $u_3 \ge u_2 + q_3$, $u_1 \ge u_3 + q_1$.[cite: 2] Adding these gives $0 \ge q_1 + q_2 + q_3 > 0$, a contradiction.[cite: 2] So no loop can avoid the school, because the school is the only node where the load resets (it has no $u$ variable).[cite: 2]

At the same time, $u_j \le Q$ means the accumulated load on any route never exceeds the bus.[cite: 2] **One constraint family does both jobs.**[cite: 2] That is why MTZ is the standard first formulation to learn, even though stronger ones exist for large instances.[cite: 2]

## Model to code[cite: 3]

| Math | `model.py` |[cite: 3]
|---|---|[cite: 3]
| $x_{ij}$ | `pulp.LpVariable(f"x_{i}_{j}", cat="Binary")` for all ordered pairs |[cite: 3]
| $u_j \in [q_j, Q]$ | `pulp.LpVariable(f"u_{j}", lowBound=q[j], upBound=Q)` |[cite: 3]
| (1), (2) | `arrive_{j}` and `leave_{j}` equality constraints |[cite: 3]
| (3) | `prob += pulp.lpSum(x[0, j] for j in N) <= K` |[cite: 3]
| (4) | `prob += u[j] >= u[i] + q[j] - Q * (1 - x[i, j])` |[cite: 3]

Routes are read back by starting at the school and following chosen arcs until the bus returns (`extract_routes`).[cite: 3]

## Result[cite: 3, 4]

Nearest-neighbor baseline: 40.11 km over 3 buses[cite: 3]
Bus 1 (23/24): School -> Maple & 3rd -> Riverside Park -> Oak Hill -> Elm Street -> School[cite: 3]
Bus 2 (24/24): School -> Station Rd -> Pine Court -> Library -> Meadow Dr -> School[cite: 3]
Bus 3 (11/24): School -> Birch Lane -> Cedar Ave -> School[cite: 3]

Optimized (proven optimal): 36.11 km over 3 buses[cite: 3]
Bus 1 (19/24): School -> Maple & 3rd -> Oak Hill -> Riverside Park -> School[cite: 3]
Bus 2 (22/24): School -> Pine Court -> Library -> Elm Street -> Meadow Dr -> School[cite: 3]
Bus 3 (17/24): School -> Cedar Ave -> Birch Lane -> Station Rd -> School[cite: 3]

Model size: 110 binary arc variables, 10 continuous load variables, 90 MTZ constraints. CBC proves optimality in about 6 seconds.[cite: 4]

## Sensitivity: questions the model can answer[cite: 4]

Each is a one-line change to `data/config.json` or `stops.csv`:[cite: 4]

* **What if a bus breaks down?** Set `buses` to 2.[cite: 4] Total capacity 48 < 58 students, so no plan exists.[cite: 4] A one-line check ($K \cdot Q < \sum q_j$) tells you that instantly.[cite: 4] The solver, on the other hand, ran for over two minutes without finishing when I tried it, because the LP relaxation stays feasible with fractional arcs and CBC has to exhaust the tree to prove infeasibility.[cite: 4] Lesson: always test the obvious necessary conditions before calling the solver.[cite: 4]
* **Is a fourth bus worth it?** Set `buses` to 4 and compare the distance saved against the cost of a driver.[cite: 4]
* **Smaller buses?** Set `capacity` to 20 and watch the routes fragment.[cite: 4]
* **A new stop.** Add a row to `stops.csv`. Nothing else changes.[cite: 4]

## Extensions[cite: 4]

* Replace Euclidean $d_{ij}$ with road distances from OpenStreetMap via `osmnx`.[cite: 4]
* Add a fixed cost per bus to the objective so the model decides how many to run.[cite: 4]
* Add ride-time limits: no student on the bus longer than 25 minutes.[cite: 4] This needs a second MTZ-style variable for elapsed time.[cite: 4]
* At 30+ stops MTZ becomes slow.[cite: 4] Compare with Google OR-Tools' routing solver, which uses local search heuristics and scales to thousands of stops.[cite: 4]

## Run[cite: 4]

```bash
python -m stage3_bus_routing.run
python -m pytest tests/test_stage3_routing.py -v
```[cite: 4]

```