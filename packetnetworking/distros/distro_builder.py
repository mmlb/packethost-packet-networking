import os
import sys
import logging
import json
from textwrap import dedent

from jinja2 import Template, StrictUndefined
from jinja2.exceptions import UndefinedError

from .. import utils

log = logging.getLogger()


def get_templates_dir(instance):
    instance_dir = os.path.abspath(
        os.path.dirname(sys.modules[instance.__class__.__module__].__file__)
    )
    return os.path.join(os.path.relpath(instance_dir, utils.package_dir), "templates")


class DistroBuilder(utils.Tasks):
    distros = None
    network_builders = []

    def __init__(self, metadata):
        self.templates_base = get_templates_dir(self)
        self.metadata = metadata
        self.network = self.metadata.network
        self.builders = []
        self.tasks = {}

    @property
    def ipv4pub(self):
        return self.network.addresses.management.public.ipv4

    @property
    def ipv6pub(self):
        return self.network.addresses.management.public.ipv6

    @property
    def ipv4priv(self):
        return self.network.addresses.management.private.ipv4

    def build(self):
        """
        Build triggers all build functions to build the list of tasks needing
        to be applied.
        """
        self.build_tasks()
        log.debug(
            "Discovered {:d} {} tasks".format(len(self.tasks), self.__class__.__name__)
        )
        found_tasks = False
        for NetworkBuilder in self.network_builders:
            builder = NetworkBuilder(self.metadata)
            if not hasattr(builder, "templates_base"):
                builder.templates_base = self.templates_base

            self.builders.append(builder)
            builder.build()
            if builder.tasks:
                log.debug(
                    "Discovered {:d} tasks from {}".format(
                        len(builder.tasks), NetworkBuilder.__name__
                    )
                )
                found_tasks = True
        return self.tasks or found_tasks

    def build_tasks(self):
        pass

    def context(self):
        return {
            "hostname": self.metadata.hostname,
            "iface0": self.network.interfaces[0],
            "interfaces": self.network.interfaces,
            "ip4priv": self.ipv4priv.first,
            "ip4pub": self.ipv4pub.first,
            "ip6pub": self.ipv6pub.first,
            "net": self.network,
            "osinfo": self.metadata.operating_system,
            "private_subnets": self.network.private_subnets,
            "resolvers": self.network.resolvers,
        }

    @property
    def has_network_tasks(self):
        if self.builders:
            for builder in self.builders:
                if builder.tasks:
                    return True
        return False

    @property
    def all_tasks(self):
        """
        all_tasks combines DistroBuilder tasks and all NetworkBuilder tasks
        into a single dictionary used by the `DistroBuilder.render` function.
        """
        tasks = {}
        if self.tasks:
            tasks.update(self.tasks)
        if self.builders:
            for builder in self.builders:
                if builder.tasks:
                    tasks.update(builder.tasks)
        return tasks

    # pylama:ignore=C901
    def render(self):
        """
        Render compiles each task template into the final content.
        """
        if not self.has_network_tasks:
            log.error("No network builder tasks discovered")
            return {}

        rendered_tasks = {}
        if not self.all_tasks:
            return {}

        for path, template in self.all_tasks.items():
            log.debug("Rendering task: '{}'".format(path))
            if template is None:
                rendered_tasks[path] = template
                continue

            file_mode = None
            mode = None
            context = self.context()
            if isinstance(template, dict):
                context.update(template.get("context") or {})
                file_mode = template.get("file_mode")
                mode = template.get("mode", None)
                template_path = template.get("template_path")
                if template_path is None:
                    template = template.get("template")
                else:
                    with open(template_path, "r") as f:
                        template = f.read()

            template = dedent(template)
            tmpl = Template(
                template,
                keep_trailing_newline=True,
                lstrip_blocks=True,
                trim_blocks=True,
                undefined=StrictUndefined,
            )

            tmpl.environment.globals.update(generated_header=utils.generated_header)

            try:
                if file_mode or mode:
                    rendered_tasks[path] = {
                        "file_mode": file_mode,
                        "mode": mode,
                        "content": tmpl.render(context),
                    }
                else:
                    rendered_tasks[path] = tmpl.render(context)
            except UndefinedError:
                # having to use print as log.* isn't printing out the json
                print(
                    "==== METADATA ====\n"
                    + json.dumps(self.metadata.as_dict(), indent=2),
                    file=sys.stderr,
                )
                log.error(
                    "An exception occured while processing task "
                    + "'{}' with template:\n{}".format(path, template)
                )
                raise
        return rendered_tasks

    def run(self, rootfs_path):
        """
        Run processes the rendered tasks and writes them to the filesystem.
        """
        rendered_tasks = self.render()
        if not rendered_tasks:
            return {}
        for relpath, content in rendered_tasks.items():
            log.debug("Processing task: '{}'".format(relpath))
            abspath = os.path.join(rootfs_path, relpath)
            if content is None:
                if os.path.lexists(abspath):
                    log.info("Removing '{}'".format(abspath))
                    os.remove(abspath)
                else:
                    log.debug(
                        "Skipped removing '{}' Path doesn't exist".format(abspath)
                    )
                continue

            # Resolve symlinks to write to the destination file
            abspath = utils.resolve_path(rootfs_path, relpath)

            file_mode = "w"
            mode = None
            if isinstance(content, dict):
                file_mode = content.get("file_mode") or file_mode
                mode = content.get("mode", None)
                content = content.get("content")

            dirname = os.path.dirname(abspath)
            if dirname and not os.path.lexists(dirname):
                log.debug("Making directory '{}'".format(dirname))
                os.makedirs(dirname, exist_ok=True)

            log.debug("Writing content to '{}'".format(abspath))
            with open(abspath, file_mode) as f:
                f.write(content)

            if mode:
                os.chmod(abspath, mode)
        return rendered_tasks


def get_distro_builder(distro):
    catch_all = None
    for builder in DistroBuilder.__subclasses__():
        if isinstance(builder.distros, list) and distro.lower() in builder.distros:
            log.debug("Using builder: {}".format(builder.__name__))
            return builder
        elif builder.distros == "*":
            catch_all = builder
    if catch_all:
        log.debug("Using catch-all builder: {}".format(catch_all.__name__))
    else:
        log.debug("No builder found for '{}' distro".format(distro))
    return catch_all
