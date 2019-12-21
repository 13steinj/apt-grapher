from re import compile as re_compile
from subprocess import PIPE, run

from graphviz import Digraph, nohtml
from os import makedirs
from sys import argv

PACKAGE_RE = re_compile("(?:^|\n)(.*)/")
DEPENDENCE_RE = re_compile(
    "\A\s*((?:\|?)(?:"
        "Recommends|"
        "Suggests|"
        "Depends|"
        "Breaks|"
        "Conflicts|"
        "Replaces|"
        "Enhances|"
        "PreDepends"
    ")):\s*(.*)\Z")


class UniqueDigraph(Digraph):
    def __init__(self, *args, **kwargs):
        self.__nodes, self.__edges = set(), set()
        super(UniqueDigraph, self).__init__(*args, **kwargs)

    def node(self, name, label=None, _attributes=None, **attrs):
        if name not in self.__nodes:
            super(UniqueDigraph, self).node(
                nohtml(name), label=label, _attributes=_attributes, **attrs)
            self.__nodes.add(name)

    def edge(self, tail_name, head_name, label=None, _attributes=None, **attrs):
        if (tail_name, head_name) not in self.__edges:
            super(UniqueDigraph, self).edge(
                nohtml(tail_name), nohtml(head_name),
                lable=label, _attributes=_attributes, **attrs)
            self.__nodes.add(tail_name)
            self.__nodes.add(head_name)
            self.__edges.add((tail_name, head_name))



class DigraphHolder(dict):
    def __init__(self, dirname, *args, **kwargs):
        self.__dirname = dirname
        super(DigraphHolder, self).__init__(*args, **kwargs)

    def render(self):
        for graph in self.values(): graph.render()

    def save(self):
        for graph in self.values(): graph.save()

    def __missing__(self, key):
        return self.setdefault(key, Digraph(key, directory=self.__dirname))


def main(output):
    makedirs(output, exist_ok=True)
    graphs = DigraphHolder(output)
    installed = PACKAGE_RE.findall(
        run("apt list --installed".split(),
            stdout=PIPE, stderr=PIPE, check=True).stdout.decode())
    completion_division = len(installed) / 100
    completion, changed = 0, False

    for n, installed_package in enumerate(installed, start=1):
        graphs["Installed"].node(installed_package)
        dependency_data = run(
            f"apt-cache depends {installed_package}".split(),
            stdout=PIPE, stderr=PIPE, check=True).stdout.decode()
        dep_type, dep_package = None, None
        for idx, dependency in enumerate(dependency_data.strip().split('\n')):
            if dependency == installed_package:
                continue
            dep_match = DEPENDENCE_RE.match(dependency)
            if dep_match:
                dep_type, dep_package = dep_match.groups()
                # graphs[dep_type].node(dep_package)
                # graphs[dep_type].node(installed_package)
                graphs[dep_type].edge(dep_package, installed_package)
            else:
                sibling = dep_package
                dep_package = dependency.strip()
                # graphs[dep_type].node(dep_package)
                # graphs[dep_type].node(sibling)
                graphs[dep_type].edge(dep_package, sibling)
                graphs[dep_type].edge(sibling, dep_package)
        if n == len(installed) and completion == 99:
            print("100%")
            continue
        else:
            new, rem = divmod(n, completion_division)
            new = int(new)
            changed = new != completion
            if changed:
                completion = new
                print(f"{completion/100:.0%}")

    graphs.save()
    graphs.render()

if __name__ == "__main__":
    main(argv[-1])
