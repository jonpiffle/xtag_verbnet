import re, heapq

from collections import deque

from grammar import Grammar
from constants import DATA_DIR

class Heap(object):
    def __init__(self, initial=None, key=lambda x: x):
        self.count = 0
        self.key = key
        if initial:
            self._data = [(key(item), item) for item in initial]
            heapq.heapify(self._data)
        else:
            self._data = []

    def push(self, item):
        self.count += 1
        heapq.heappush(self._data, (self.key(item), self.count, item))
 
    def pop(self):
        return heapq.heappop(self._data)[1]

class State(object):
    def __init__(self, n, goal, pos, fl, fr, state_type, hw, postag, blist):
        self.n = n
        self.goal = goal
        self.pos = pos
        self.fl = fl
        self.fr = fr
        self.state_type = state_type
        self.hw = hw
        self.postag = postag
        self.blist = blist

    def node_eq(self, n, other):
        return n.tree_name == other.tree_name and str(n.anchors()) == str(other.anchors())

    def __eq__(self, other):
        return self.node_eq(self.n, other.n) and self.node_eq(self.goal, other.goal) and self.pos == other.pos //
            and self.fl == other.fl and self.fr == other.fr and self.state_type == other.state_type //
            and self.hw = other.hw and self.pos_tag == other.pos_tag

class Proc(object):
    def __init__(self, i, j, state):
        self.i = i
        self.j = j
        self.state = state

class Chart(object):
    def __init__(self, k):
        self.TOP = "S"
        self.agenda = deque([])
        self.unigram_dict = self.load_unigram_data()
        self.grammar = Grammar.load()
        self.grammar.filter(set(self.unigram_dict.keys()))
        self.array = [[Heap(key=lambda s: self.unigram_dict[s.n.tree_name]) for i in range(k)] for j in range(k)] 

    def add(self, i, j, state):
        sheap = self.array[i][j]
        sheap.push(state)
        proc = Proc(i, j, state)
        self.agenda.append(proc)

    def init_rootnodes(self, label):
        return self.grammar.init_trees_from_label(label)

    def nodetype(self, n):
        if n.anchor:
            return "ANCHOR"
        elif n.lex:
            return "TERMINAL"
        elif n.subst:
            return "SUBST"
        elif n.prefix() == "epsilon":
            return "EPS"
        elif n.foot:
            return "FOOT"
        else:
            return "INTERNAL"

    def init_head(self, p):
        s = p.state

        if not s.n.initial():
            return 

        hc = self.headcorner(s.n)

    def headcorner(self, n):
        if n.is_root() and n.auxiliary():
            return n.foot_node()
        elif n.is_root():
            return n.anchor_positions()[0]
        else:
            # return n if terminal
            if len(n) == 0:
                return n

            #leftmost child of n
            node = n[0] 
            while node != n:
                new_hc = self.headcorner(node)

            # find headcorner of leftmost child
            new_hc = hand_find_headcorner(new, node);
            #get node type of that headcorner
            new_hctype = hand_nodetype(new, new_hc);

            myassert(new_hctype != IS_INTERNAL);

            # set new to headcorner
            new->headcorner_tbl[node] = new_hc;

            # if new_hctype has precedence over hctype
            # update headcorner
            if (hand_cmp_headcorner(hctype, new_hctype) > 0) {
                hc = new_hc;
                hctype = new_hctype;
            }

            # set node to neighbor or null (i think -- this has complexity due to tree binarization. it may get set to a parent)
            node = hand_rightnode(new, node))
         }


    def move_up(self, p):
        pass

    def completer(self, p):
        pass

    def get_derivations(self, symbol):
        pass

    def load_unigram_data(sefl, filename=DATA_DIR+"unigram.data"):
        lines = open(filename, 'r').readlines()
        unigram_dict = {}
        for l in lines:
            if '\x02' not in l and '\x03' not in l:
                continue
            count = int(re.search(r'(\d+)', l).group(1))
            name = re.search(r'"(.+)"', l).group(1).replace('\x02', 'alpha').replace('\x03', 'beta')
            unigram_dict[name] = count
        return unigram_dict

def hparse(sentence):
    start = 0
    k = len(sentence) + 1
    chart = Chart(k)
    N = chart.init_rootnodes(chart.TOP)

    for n in N:
        state = State(n, n, "top", None, None, "init", None, None, [])
        chart.add(start, k-1, state)

    while len(chart.agenda) > 0:
        p = chart.agenda.popleft()
        n1list = chart.init_head(p)
        n2list = chart.move_up(p)
        n3list = chart.completer(p)

    chart.get_derivations(chart.TOP)

if __name__ == '__main__':
    example = ["dog", "chased", "cat"]
    hparse(example)