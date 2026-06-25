import networkx as nx
import matplotlib.pyplot as plt
import os
from lure.node.net.physical import CartesianPhysical


class Grapher:
    """Graphs topologies in the simulation"""

    def __init__(self, nodes, output_dir):
        self.nodes = nodes
        self.topology_output = output_dir + "/topologies/"
        os.makedirs(self.topology_output, exist_ok=True)

    def graph_network(self):
        """Graphs network topology"""
        G = nx.Graph()
        if isinstance(self.nodes[0].netstack.physical, CartesianPhysical):
            for n in self.nodes:
                G.add_node(n.node_id, pos=n.netstack.physical.position)
        else:
            for n in self.nodes:
                G.add_node(n.node_id)
        for n in self.nodes:
            routes = n.netstack.network.routes
            net_neighbors = []
            for dest, next_hop in routes.items():
                if next_hop not in net_neighbors:
                    net_neighbors.append(next_hop)
            for neighbor in net_neighbors:
                if not G.has_edge(n.node_id, int(neighbor)):
                    G.add_edge(n.node_id, int(neighbor))
        if isinstance(self.nodes[0].netstack.physical, CartesianPhysical):
            pos = nx.get_node_attributes(G, "pos")
            nx.draw_networkx(G=G, pos=pos)
        else:
            nx.draw_networkx(G=G, pos=nx.planar_layout(G=G))
        plt.title("Network")
        plt.savefig(self.topology_output + "network.png")
        plt.close()

    def graph_physical(self):
        """Graphs physical topology"""
        G = nx.Graph()
        # Use this to set positions later on
        if isinstance(self.nodes[0].netstack.physical, CartesianPhysical):
            for n in self.nodes:
                G.add_node(n.node_id, pos=n.netstack.physical.position)
            for n in self.nodes:
                n_neighbors = [
                    n.netstack.physical.get_neighbor_by_id(x)
                    for x in n.netstack.physical.neighbor_list
                ]
                for neighbor in n_neighbors:
                    if not G.has_edge(n.node_id, int(neighbor.addr)):
                        G.add_edge(n.node_id, int(neighbor.addr))
            pos = nx.get_node_attributes(G, "pos")
            nx.draw_networkx(G=G, pos=pos)
        else:
            for n in self.nodes:
                G.add_node(n.node_id)
            for n in self.nodes:
                n_neighbors = [
                    n.netstack.physical.get_neighbor_by_id(x)
                    for x in n.netstack.physical.neighbor_list
                ]
                for neighbor in n_neighbors:
                    if not G.has_edge(n.node_id, int(neighbor.addr)):
                        G.add_edge(n.node_id, int(neighbor.addr))
            nx.draw_networkx(G=G, pos=nx.kamada_kawai_layout(G=G))
        plt.title("Physical")
        plt.savefig(self.topology_output + "physical.png")
        plt.close()
