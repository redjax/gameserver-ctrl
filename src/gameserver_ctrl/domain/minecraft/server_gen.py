from pydantic import BaseModel, Field, validator, ValidationError
from typing import Union

from uuid import UUID, uuid4
from pathlib import Path

from loguru import logger as log

from gameserver_ctrl.constants import DATA_DIR, TEMPLATES_DIR, OUTPUT_DIR
from gameserver_ctrl.utils import jinja_utils

## Import jinja2 classes for typing & autocomplete
from jinja2 import FileSystemLoader, Environment, Template

mc_templates_dir: str = f"{TEMPLATES_DIR}/minecraft"
mc_dotenv_dir: str = f"{mc_templates_dir}/dotenv"
mc_json_dir: str = f"{mc_templates_dir}/json"
mc_scripts_dir: str = f"{mc_templates_dir}/scripts"
mc_containers_dir: str = f"{mc_templates_dir}/server_containers"

mc_filegen_output_dir: str = f"{OUTPUT_DIR}/minecraft/"

from .schemas import (
    ForgeServerEnvFile,
    ForgeServerComposeFile,
    ForgeServerEnvData,
    WhitelistFile,
    WhitelistPlayer,
)


class MCForgeServer(BaseModel):
    """Class representation of a complete Dockerized Minecraft Forge server.

    This class is composed from other classes (ForgeServerEnvFile, WhitelistFile, etc),
    and outputs a set of templates for a new server.

    Params:
    -------

    name (str): ...

    output_path (str): ...

    init_dirs (list[str]): ...

    env_file (str): ...

    whitelist_file (str): ...

    compose_file (str): ...
    """

    name: str | None = Field(default="example_forge_server")
    output_path: str | None = Field(default=mc_filegen_output_dir)
    init_dirs: list[str] | None = ["data"]

    env_file: ForgeServerEnvFile | None = Field(default=None)
    whitelist_file: WhitelistFile | None = Field(default=None)
    compose_file: ForgeServerComposeFile | None = Field(default=None)

    @property
    def output_dir(self) -> str:
        if self.output_path:
            if not Path(self.output_path).exists():
                Path(self.output_path).mkdir(parents=True)

        _out_dir = f"{self.output_path}/{self.name}"

        return _out_dir.replace("//", "")

    def create_server(self) -> None:
        """Compile & render Minecraft Forge server files."""
        if self.output_dir:
            if not Path(self.output_dir).exists():
                Path(self.output_dir).mkdir(parents=True)

        for dir in self.init_dirs:
            if not Path(f"{self.output_dir}/{dir}").exists():
                Path(f"{self.output_dir}/{dir}").mkdir(parents=True)

        ## Set output path for server files
        self.env_file.output_path = self.output_dir
        self.whitelist_file.output_path = self.output_dir
        self.compose_file.output_path = self.output_dir

        if Path(self.output_dir).exists():
            log.warning(
                FileExistsError(
                    f"Did not render Minecraft server template. Output directory already exists: {self.output_dir}."
                )
            )
        else:
            ## Render server files
            try:
                self.env_file.render_to_file()
            except Exception as exc:
                msg = Exception(
                    f"Unhandled exception rendering .env file. Details: {exc}"
                )
                log.error(msg)

                raise msg
            try:
                self.whitelist_file.render_to_file()
            except Exception as exc:
                msg = Exception(
                    f"Unhandled exception rendering whitelist.json file. Details: {exc}"
                )
                log.error(msg)

                raise msg
            try:
                self.compose_file.render_to_file()
            except Exception as exc:
                msg = Exception(
                    f"Unhandled exception rendering docker-compose.yml file. Details: {exc}"
                )
                log.error(msg)

                raise msg


class RecreateServerScript(BaseModel):
    name: str = "recreate_server"
    ext: str = "sh"

    output_path: str | None = Field(default=None)
    template_dir: str | None = Field(default=mc_scripts_dir)
    template_file: str | None = Field(default="template_recreate_server_sh.j2")

    server: MCForgeServer | None = Field(default=None)

    @property
    def filename(self) -> str:
        _filename = f"{self.name}.{self.ext}"

        return _filename

    @property
    def output_file(self) -> str:
        if self.output_path:
            if not Path(self.output_path).exists():
                Path(self.output_path).mkdir(parents=True)

            _outfile = f"{self.output_path}/{self.filename}"

        else:
            _outfile = f"{self.filename}"

        return _outfile

    @property
    def template_path(self) -> str:
        """
        Create path string to template_file.
        """

        _template_path = f"{self.template_dir}/{self.template_file}"

        return _template_path

    @property
    def template_loader(self) -> FileSystemLoader:
        """
        Return a jinja2.FileSystemLoader object for the template_dir.

        This loader is passed to the environment created in the
        template_env property.
        """

        _loader = jinja_utils.load_template_dir(f"{self.template_dir}")

        return _loader

    @property
    def template_env(self) -> Environment:
        """
        Return a jinja2.Environment object from the template_loader property.

        This environment can be used to create jinja2.Template objects. The environment
        prepares the .j2 template file for manipulation.
        """

        _env = jinja_utils.create_loader_env(_loader=self.template_loader)

        return _env

    @property
    def template(self) -> Template:
        """
        Return a jinja2.Template object.

        This template is used to create an output, i.e. with the .render()
        function. This render can then be exported to a file with
        WhitelistFile.render_to_file().
        """

        ## Check if the template_path exists
        if Path(self.template_path).exists():
            ## Create Template object
            _template = jinja_utils.get_template_from_env(
                templ_env=self.template_env,
                templ_file=f"{self.template_file}",
            )

        ## Could not find template
        else:
            ValueError(f"Can't find template at path: {self.template_path}")

        return _template

    @property
    def template_render(self) -> str:
        """
        Return a string of the rendered Template.
        """

        _render = self.template.render(server_obj=self.server)

        return _render

    def render_to_file(self) -> None:
        """
        Output rendered Template string to a file.
        """

        try:
            jinja_utils.render_template_to_file(
                _render=self.template_render, _outfile=self.output_file
            )

            return_obj = {
                "success": True,
                "reason": f"Successfully rendered template to: [{self.output_file}]",
            }
        except:
            return_obj = {
                "success": False,
                "reason": f"Uncaught exception rendering template to: [{self.output_file}]",
            }

        return return_obj
