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


class WhitelistPlayer(BaseModel):
    """Class representation of Minecraft whitelist.json player file.

    A Minecraft player in the whitelist.json file is structured like:
    {"id": <uuid-string>, "name": <string>}

    Params:
    -------

    id (str): A UUID-like string of the Minecraft player's ID
    name (str): A Minecraft username. Must match the ID on Minecraft's servers
    """

    id: str | None = Field(default=None)
    name: str | None = Field(default=None)


class WhitelistFile(BaseModel):
    """Class representation of a Minecraft whitelist.json file.

    Uses the data passed in whitelist_players to create the template.
    This class uses properties to create jinja2 objects, such as a FileSystemLoader,
    and creates a rendered template that can be written to a file with
    WhitelistFile.render_to_file().

    Params:

    name (str): TODO
    ext (str): TODO
    output_path (str): TODO
    template_dir (str): TODO
    template_file (str): TODO
    whitelist_players (list[WhitelistPlayer]): TODO
    """

    ## Minecraft servers expect the file to be named "whitelist.json"
    name: str | None = Field(default="whitelist")
    ext: str | None = Field(default="json")

    ## Path (not including filename) to output the whitelist file to
    output_path: str | None = Field(default=None)
    ## Template directory to search for template_file below
    template_dir: str | None = Field(default=mc_json_dir)
    ## Name of template file to load
    template_file: str | None = Field(default="template_server_whitelist.j2")
    ## Python list of WhitelistPlayer objects to pass to whitelist template
    whitelist_players: list[WhitelistPlayer] | None = Field(default=None)

    @property
    def filename(self) -> str:
        """
        Create filename by concatenating this objects name & ext values.
        """

        _filename = f"{self.name}.{self.ext}"

        return _filename

    @property
    def output_file(self) -> str:
        """
        Dynamically create path to save whitelist.json file to
        """

        if self.output_path:
            if not Path(self.output_path).exists():
                ## Create output_path dir if it does not exist
                Path(self.output_path).mkdir(parents=True)

            ## Concatenate output_path & filename to create outfile string
            _outfile = f"{self.output_path}/{self.filename}"

        else:
            ## No path detected, simply output the filename to the root dir of script
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

        _render = self.template.render(whitelist_players=self.whitelist_players)

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


class ForgeServerEnvData(BaseModel):
    """Class representation of a Minecraft Docker .env file.

    Note: This class only stores the data to pass to the .env template.
    Use the ForgeServerEnvFile to generate the template, which will load
    from the parameters of this class.

    Params:
    -------

    image_tag (str): TODO
    container_name (str): TODO
    server_port (int): TODO
    server_type (str): TODO
    server_ver (str): TODO
    server_debug (bool): TODO
    whitelist_enable (bool): TODO
    mods_dir (str): TODO
    whitelist_file (str): TODO
    whitelist_override (bool): TODO
    modrinth_project_slugs (str): TODO
    """

    image_tag: str | None = Field(default=None)
    container_name: str | None = Field(default=None)
    server_port: int | None = Field(default=0)
    server_type: str | None = Field(default=None)
    server_ver: str | None = Field(default=None)
    server_debug: bool | None = Field(default=False)
    whitelist_enable: bool | None = Field(default=False)
    mods_dir: str | None = Field(default=None)
    whitelist_file: str | None = Field(default=None)
    whitelist_override: bool | None = Field(default=False)
    modrinth_project_slugs: str | None = Field(default=None)

    @property
    def project_slugs(self) -> str:
        _slugs = self.modrinth_project_slugs.replace(", ", ",")

        return _slugs


class ForgeServerEnvFile(BaseModel):
    """Class representation of a Minecraft Docker .env file.

    Params:
    -------

    name (str): TODO
    ext (str): TODO
    output_path (str): TODO
    template_dir (str): TODO
    template_file (str): TODO
    env_data (ForgeServerEnvData): TODO
    """

    name: str | None = Field(default=".env")
    ext: str | None = Field(default=None)

    output_path: str | None = Field(default=None)
    template_dir: str | None = Field(default=mc_dotenv_dir)
    template_file: str | None = Field(default="template_compose_forge_mod_dotenv.j2")

    env_data: ForgeServerEnvData | None = Field(default=None)

    @property
    def output_file(self) -> str:
        """
        Dynamically create path to save whitelist.json file to
        """

        if self.output_path:
            if not Path(self.output_path).exists():
                ## Create output_path dir if it does not exist
                Path(self.output_path).mkdir(parents=True)

            ## Concatenate output_path & filename to create outfile string
            _outfile = f"{self.output_path}/{self.name}"

        else:
            ## No path detected, simply output the filename to the root dir of script
            _outfile = f"{self.name}"

        return _outfile.replace("//", "")

    @property
    def template_path(self) -> str:
        """
        Create path string to template_file.
        """

        _template_path = f"{self.template_dir}/{self.template_file}"

        return _template_path.replace("//", "")

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

        _render = self.template.render(env_data=self.env_data)

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


class ForgeServerComposeFile(BaseModel):
    """Class representation of a Minecraft Forge docker-compose.yml file.

    Params:
    -------

    name (str): TODO
    ext (str): TODO
    output_path (str): TODO
    template_dir (str): TODO
    template_file (str): TODO
    compose_ver (str): TODO
    """

    name: str | None = Field(default="docker-compose")
    ext: str | None = Field(default="yml")

    output_path: str | None = Field(default=None)
    template_dir: str | None = Field(default=f"{mc_containers_dir}/forge_server")
    template_file: str | None = Field(default="template_docker-compose.j2")

    compose_ver: str | None = Field(default="3.8")

    @validator("output_path")
    def valid_output_path(cls, v) -> str:
        v.strip("/")

        return v

    @property
    def filename(self) -> str:
        """
        Create filename by concatenating this objects name & ext values.
        """

        _filename = f"{self.name}.{self.ext}"
        log.debug(f"[{self.name}] Filename: {_filename}")

        return _filename

    @property
    def output_file(self) -> str:
        """
        Dynamically create path to save whitelist.json file to
        """

        if self.output_path:
            if not Path(self.output_path).exists():
                ## Create output_path dir if it does not exist
                Path(self.output_path).mkdir(parents=True)

            ## Concatenate output_path & filename to create outfile string
            _outfile = f"{self.output_path}/{self.filename}"

        else:
            ## No path detected, simply output the filename to the root dir of script
            _outfile = f"{self.filename}"

        log.debug(f"[{self.name}] Outfile: {_outfile}")

        return _outfile.replace("//", "")

    @property
    def template_path(self) -> str:
        """
        Create path string to template_file.
        """

        _template_path = f"{self.template_dir}/{self.template_file}"
        log.debug(f"[{self.name}] Template path: {_template_path}")

        return _template_path.replace("//", "")

    @property
    def template_loader(self) -> FileSystemLoader:
        """
        Return a jinja2.FileSystemLoader object for the template_dir.

        This loader is passed to the environment created in the
        template_env property.
        """

        _loader = jinja_utils.load_template_dir(f"{self.template_dir}")
        log.debug(f"[{self.name}] Template loader: {_loader}")

        return _loader

    @property
    def template_env(self) -> Environment:
        """
        Return a jinja2.Environment object from the template_loader property.

        This environment can be used to create jinja2.Template objects. The environment
        prepares the .j2 template file for manipulation.
        """

        _env = jinja_utils.create_loader_env(_loader=self.template_loader)
        log.debug(f"[{self.name}] Template env: {_env}")

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

        _render = self.template.render()

        return _render

    def render_to_file(self) -> dict[str, bool]:
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

        log.debug(f"[{self.name}] return object: {return_obj}]")

        return return_obj
