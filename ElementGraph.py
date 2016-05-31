from Graph import *
import copy

class ElementGraph(Graph):
	"""An element graph is a graph with a root element"""
	
	def __init__(self,id,type,name=None, Elements = set(), root_element = None, Edges = set(), Constraints = set()):
		super(ElementGraph,self).__init__(\
											id,\
											type,\
											name,\
											Elements,\
											Edges,\
											Constraints\
										)
		self.root = root_element		
		
	def copyGen(self):
		yield copy.deepcopy(self)
		
	def getElementGraphFromElement(self, element, Type):
		if self.root is element:
			return self
		
		return Type(element.id, \
					type='element %s' %subgraph, \
					name=self.name,\
					Elements = self.rGetDescendants(element),\
					root_element = element,\
					Edges = self.rGetDescendantEdges(element),\
					Constraints = self.rGetDescendantConstraints(element)\
					)
					
	def swap(self, source, other):
		"""	Completely replaces source with other.root and all descending
			Assumes that other has already merged important parts of descendants of source
			1) Remove source's subtree, 2) add other
			
		"""
		#If an operator, make sure to mergeArgs
		
		#Step 1: remove all descendant edges
		{self.edges.remove(edge) for edge in self.edges if edge.source.isIdentical(source)}
		self.edges.union(
						{edge.swapSource(other.root) \
							for edge in self.edges \
								if not source.merge(edge) is None
						})
				
		{edge.swapSink(other.root) for edge in self.edges if source.isIdentical(edge.sink)}
		{self.edges.remove(edge) for edge in self.rGetDescendantEdges(source)}
		{self.elements.remove(element) for element in self.rGetDescendants(source)}
		{self.constraints.remove(edge) for edge in self.rGetDescendantConstraints(source)}
		return self
			
	def mergeEdgesFromSource(self, other, edge_source, mergeable_edges = set()):
		""" Accommodates, does not merge the edges, merges source"""
		if edge_source.merge(other.root) is None:
			return None
			
		if len(mergeable_edges) == 0:
			return None
			
		new_incident_edges = {edge.swapSource(edge_source) for edge in mergeable_edges}
		
		self.edges.update(new_incident_edges)
	
		for new_edge in new_incident_edges:
			self.elements.add(new_edge.sink)
			self.elements.update(other.rGetDescendants(new_edge.sink)) #Try using Generator
			
			self.edges.update(other.rGetDescendantEdges(new_edge.sink))
			self.constraints.update(other.rGetDescendantConstraints(new_edge.sink))
	
		return self		
			
	def mergeAt(self, other, edge_source):
		""" Steals all edges from other, adds edges to edges_source"""
		""" All edges are 'Accomodated' """"
		return self.mergeEdgesFromSource(	other, \
											edge_source, \
											other.getIncidentEdges(other.root)\
										)
		
	def getConsistentEdgePairs(self, incidentEdges, otherEdges):
		return {(edge,other_edge) \
					for edge in incidentEdges \
							for other_edge in otherEdges \
									if edge.isConsistent(other)\
				}
				
	def getInconsistentEdges(self, other_edges, consistent_edge_pairs):
		"""Returns set, because parameter mergeable edges in mergeEdgesFromSource takes set"""
		return {other_edge \
					for other_edge in otherEdges \
						if other_edge not in \
							(oe for (e,oe) in consistent_edge_pairs\
						)\
				}
	
	def Merge(self, other):
		return self.rMerge(other, self.root)
	
	def rMerge(self, other, self_element, consistent_merges = set()):
		""" Returns set of consistent merges, which are Edge Graphs of the form self.merge(other)""" 
		#self_element.merge(other_element)
		
		#Get next edges
		otherEdges = other.getIncidentEdges(other.root)
		print('how many incident edges: ', len(otherEdges))
		#BASE CASE
		if len(otherEdges) == 0:
			return {self}
			
		
		consistent_edge_pairs = self.getConsistentEdgePairs(self.getIncidentEdges(self_element), \
															otherEdges\
															)
															
		#If they're all inconsistent, then let's just get to den, aye?
		if len(consistent_edge_pairs) == 0:
			if self.mergeAt(other, self_element) is None:
				return None
			return {self}
			
		#INDUCTION	
		
		#First, merge inconsistent other edges, do this on every path
		self.mergeEdgesFromSource(	other, \
									self.element, \
									getInconsistentEdges(\
														otherEdges,\
														consistent_edge_pairs\
														)\
									) 
										
		#For each pair of consistent edges, create a copy of self and see what happens if we merge sinks and rMerge onward
		#For each consistent_edge, try assimilating, and try accomodating. For each one that works,
		edge_mapper = {}
		for e,oe in consistent_edge_pairs:
			accomodate_self = self.getElementGraphFromElement(e.sink, e.sink.type)
			assimilate_self = self.getElementGraphFromElement(e.sink, e.sink.type)
			to_merge 		= other.getElementGraphFromElement(oe.sink, oe.sink.type)
	
			#Can we rMerge from the sinks? (Let this be the same edge)
			assimilate_merges = assimilate_self.rMerge(to_merge)
			
			#Can we accomodate this new edge (let this be a new edge)
			
			if not type(e.sink) == Literal\
				and not accomodate_self.mergeEdgesFromSource(	other, \
																e.sink, \
																{o}\
															) 	is None:
				accomodate_merges = accomodate_self.rMerge(to_merge)
			else:
				accomodate_merges = set()
				
			if len(assimilate_merges) ==0 and len(accomodate_merges) == 0:
				"""e.sink has no consistent merge with other.sink"""
				print('e.sink has no consistent merge with other.sink')
				return None
			
			edge_mapper[e.sink].update(assimilate_merges)
			edge_mapper[e.sink].update(accomodate_merges)
		
		#Then, for each entry edge, pick a merge and move on. If we get through the whole thing, then we've found a consistent_merge
		
		return self.rCreateConsistentMerges(	set(edge_mapper.keys()),\
												edge_mapper,\
												consistent_merges\
											)
											
		#return consistent_merges
	
	def rCreateConsistentMerges(self, 	sinks_remaining = set(), \
										edge_mapper = {}, \
										complete_merges = set()):
		""" Given a set of sinks and a set of strategies per sink, 
			Find a strategy per sink, swap in strategy in self.copy
		"""
		#Base Case				
		if len(sinks_remaining) == 0:
			return self

		sink = sinks_remaining.pop()
		# complete_merges.update	({\
				# self.copyGen().swap(sink,strategy).\
					# rCreateConsistentMerges	(\
											# sinks_remaining,\
											# edge_mapper,\
											# complete_merges\
											# )\
									 # for strategy in edge_mapper[sink]\
									# })
								
		strategies = edge_mapper[sink]
		for strategy in edge_mapper[sink]:
			self_copy = self.copyGen()
			#Swap: given strategy/graph, pin the root onto sink element
			self_copy.swap(sink, strategy)
			complete_merges.update(self_copy.rCreateConsistentMerges(	sinks_remaining,\
																		edge_mapper,\
																		complete_merges))
			
		return complete_merges


def extractElementsubGraphFromElement(G, element, Type):
	Edges = G.rGetDescendantEdges(element)
	Elements = G.rGetDescendants(element)
	Constraints = G.rGetDescendantConstraints(element)
	return Type(	element.id,\
					type = element.type, \
					name=element.name, \
					Elements = Elements, \
					root_element = element,\
					Edges = Edges, \
					Constraints = Constraints\
				)
	