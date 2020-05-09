from networkx import DiGraph, add_path


class ClarkWright:
    """
    Clark & Wrights savings algorithm.

    Args:
        G (DiGraph): Graph on which algorithm is run.
        load_capacity (int, optional) : Maximum load per route. Defaults to None.
        duration (int, optional) : Maximum duration per route. Defaults to None.
        num_stops (int, optional) : Maximum number of stops per route. Defaults to None.
    """

    def __init__(self, G, load_capacity=None, duration=None, num_stops=None):
        self.G = G
        self.savings = {}
        self.ordered_edges = []
        self.route = {}
        self.best_routes = []

        self.load_capacity = load_capacity
        self.duration = duration
        self.num_stops = num_stops

    def run(self):
        """Runs Clark & Wrights savings algorithm."""
        self.initialize_routes()
        self.get_savings()
        self.processed_nodes = []
        for (i, j) in self.ordered_edges:
            self.process_edge(i, j)
        self.update_routes()

    def initialize_routes(self):
        """Initialization with round trips (Source - node - Sink)."""
        for v in self.G.nodes():
            if v not in ["Source", "Sink"]:
                # Create round trip
                round_trip_cost = (
                    self.G.edges["Source", v]["cost"] + self.G.edges[v, "Sink"]["cost"]
                )
                route = DiGraph(cost=round_trip_cost)
                add_path(route, ["Source", v, "Sink"])
                self.route[v] = route
                # Initialize route attributes
                if self.load_capacity:
                    route.graph["load"] = self.G.nodes[v]["demand"]
                if self.duration:
                    route.graph["time"] = (
                        self.G.nodes[v]["service_time"]
                        + self.G.edges["Source", v]["time"]
                        + self.G.edges[v, "Sink"]["time"]
                    )

    def update_routes(self):
        """Stores best routes found and creates its id."""
        route_id = 1
        for route in list(set(self.route.values())):
            route.graph["name"] = route_id
            route_id += 1
            self.best_routes.append(route)
        self.best_value = sum([r.graph["cost"] for r in self.best_routes])
        # for v in self.route:
        #    self.route[v] = [self.route[v]]

    def get_savings(self):
        """Computes Clark & Wright savings and orders edges by non increasing savings."""
        for (i, j) in self.G.edges():
            if i != "Source" and j != "Sink":
                self.savings[(i, j)] = (
                    self.G.edges[i, "Sink"]["cost"]
                    + self.G.edges["Source", j]["cost"]
                    - self.G.edges[i, j]["cost"]
                )
        self.ordered_edges = sorted(self.savings, key=self.savings.get, reverse=True)

    def merge_route(self, existing_node, new_node, depot):
        """
        Merges new_node in existing_node's route.
        Two possibilities:
            1. If existing_node is a predecessor of Sink, new_node is inserted
               between existing_node and Sink;
            2. If existing_node is a successor of Source, new_node is inserted
               between Source and and existing_node.
        """
        route = self.route[existing_node]
        # Insert new_node between existing_node and Sink
        if depot == "Sink":
            add_path(route, [existing_node, new_node, "Sink"])
            route.remove_edge(existing_node, "Sink")
            # Update route cost
            self.route[existing_node].graph["cost"] += (
                self.G.edges[existing_node, new_node]["cost"]
                + self.G.edges[new_node, "Sink"]["cost"]
                - self.G.edges[existing_node, "Sink"]["cost"]
            )

        # Insert new_node between Source and existing_node
        if depot == "Source":
            add_path(route, ["Source", new_node, existing_node])
            route.remove_edge("Source", existing_node)
            # Update route cost
            self.route[existing_node].graph["cost"] += (
                self.G.edges[new_node, existing_node]["cost"]
                + self.G.edges["Source", new_node]["cost"]
                - self.G.edges["Source", existing_node]["cost"]
            )

        # Update route load
        if self.load_capacity:
            self.route[existing_node].graph["load"] += self.G.nodes[new_node]["demand"]
        # Update route duration
        if self.duration:
            self.route[existing_node].graph["time"] += (
                self.G.edges[existing_node, new_node]["time"]
                + self.G.edges[new_node, "Sink"]["time"]
                + self.G.nodes[new_node]["service_time"]
                - self.G.edges[existing_node, "Sink"]["time"]
            )
        # Update processed vertices
        self.processed_nodes.append(new_node)
        if existing_node not in self.processed_nodes:
            self.processed_nodes.append(existing_node)

        self.route[new_node] = route
        return route

    def constraints_met(self, existing_node, new_node):
        """Tests if new_node can be merged in route without violating constraints."""
        route = self.route[existing_node]
        # test if new_node already in route
        if new_node in route.nodes():
            return False
        # test capacity constraints
        if self.load_capacity:
            if (
                route.graph["load"] + self.G.nodes[new_node]["demand"]
                > self.load_capacity
            ):
                return False
        # test duration constraints
        if self.duration:
            # this code assumes the times to go from the Source and to the Sink are equal
            if (
                route.graph["time"]
                + self.G.edges[existing_node, new_node]["time"]
                + self.G.edges[new_node, "Sink"]["time"]
                + self.G.nodes[new_node]["service_time"]
                - self.G.edges[existing_node, "Sink"]["time"]
                > self.duration
            ):
                return False
        # test stop constraints
        if self.num_stops:
            # Source and Sink don't count (hence -2)
            if len(route.nodes()) - 2 + 1 > self.num_stops:
                return False
        return True

    def process_edge(self, i, j):
        """
        Attemps to merge nodes i and j together.
        Merge is possible if :
            1. vertices have not been merged already;
            2. route constraints are met;
            3. either:
               a) node i is adjacent to the Source (j is inserted in route[i]);
               b) or node j is adjacent to the Sink (i is inserted in route[j]).
        """
        merged = False
        if (
            j not in self.processed_nodes  # 1
            and self.constraints_met(i, j)  # 2
            and i in self.route[i].predecessors("Sink")  # 3b
        ):
            self.merge_route(i, j, "Sink")
            merged = True

        if (
            not merged
            and (j, i) in self.G.edges()
            and i not in self.processed_nodes  # 1
            and self.constraints_met(j, i)  # 2
            and j in self.route[j].successors("Source")  # 3a
        ):
            self.merge_route(j, i, "Source")


class RoundTrip:
    """
    Computes simple round trips from the depot to each node (Source-node-Sink).

    Args:
        G (DiGraph): Graph on which round trips are computed.
    """

    def __init__(self, G):
        self.G = G
        self.route = {}
        self.round_trips = []

    def run(self):
        route_id = 0
        for v in self.G.nodes():
            if v not in ["Source", "Sink"]:
                route_id += 1
                if ("Source", v) in self.G.edges():
                    cost_1 = self.G.edges["Source", v]["cost"]
                else:
                    # If edge does not exist, create it with a high cost
                    cost_1 = 1e10
                    self.G.add_edge("Source", v, cost=cost_1)
                if (v, "Sink") in self.G.edges():
                    cost_2 = self.G.edges[v, "Sink"]["cost"]
                else:
                    # If edge does not exist, create it with a high cost
                    cost_2 = 1e10
                    self.G.add_edge(v, "Sink", cost=cost_2)
                total_cost = cost_1 + cost_2
                route = DiGraph(name=route_id, cost=total_cost)
                route.add_edge("Source", v, cost=cost_1)
                route.add_edge(v, "Sink", cost=cost_2)
                self.route[v] = route
                self.round_trips.append(route)
