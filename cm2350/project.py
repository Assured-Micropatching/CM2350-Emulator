import sys
import time
import logging
import os.path
import weakref
import argparse

# Import any custom file parsers, this will cause any parsers to get patched 
# into the vivisect.parsers package
import cm2350.parsers

import envi.cli as e_cli
import envi.exc as e_exc
import envi.common as e_common
import envi.config as e_config

import vivisect
import vivisect.cli as viv_cli
import vivisect.base as viv_base
import vivisect.const as viv_const


__all__ = [
    'VivProject',
    'merge_dict',
]


# Force the asnycio and parso modules to not use the standard logging level
logging.getLogger('parso').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


def merge_dict(base, update):
    if not (isinstance(base, dict) and isinstance(update, dict)):
        raise Exception('Cannot merge %r and %r' % (base, update))

    # Start the merged dict with unique keys from the base dict
    ret = dict((k, v) for k, v in base.items() if k not in update)

    # Add in any unique keys from the update dict
    ret.update((k, v) for k, v in update.items() if k not in base)

    # Merge the rest of the keys
    merge_keys = [k for k in base.keys() if k in update]
    for key in merge_keys:
        if isinstance(base[key], dict):
            ret[key] = merge_dict(base[key], update[key])
        else:
            # If the key is in both dicts the "update" dict has priority
            ret[key] = update[key]

    return ret


class VivProjectMeta(type):
    def __new__(cls, name, bases, attrs):
        """
        Merge the defconfig and docconfig from all super classes into one
        single class for the new class
        """
        defconfig = {}
        docconfig = {}

        # First merge the defaults and docs from the base classes.  Do this in
        # reverse order so the classes earlier in the bases list have lower
        # priority
        for basecls in reversed(bases):
            if hasattr(basecls, 'defconfig'):
                defconfig = merge_dict(defconfig, basecls.defconfig)

            if hasattr(basecls, 'docconfig'):
                docconfig = merge_dict(docconfig, basecls.docconfig)

        # Now add in the defaults and docs from the new class if defined
        if 'defconfig' in attrs:
            attrs['defconfig'] = merge_dict(defconfig, attrs['defconfig'])

        if 'docconfig' in attrs:
            attrs['docconfig'] = merge_dict(docconfig, attrs['docconfig'])

        return super(VivProjectMeta, cls).__new__(cls, name, bases, attrs)


class VivProject(metaclass=VivProjectMeta):
    # generic project-related defaults
    defconfig = {
        'project': {
            'name': '',
            'platform': 'unknown',
            'arch': 'unknown',
            'bigend': False,
        }
    }

    # generic project-related configuration values
    docconfig = {
        'project': {
            'name': 'Project-specific name used to organize the config and temporary files used by the project',
            'platform': 'What platform is this project',
            'arch': 'The architecture for the project',
            'bigend': 'Is the architecture Big-Endian (MSB)?',
        }
    }

    def __init__(self, defconfig=None, docconfig=None, args=None, parser=None):
        """
        Adapted from the standard vivisect.vivbin.main() function to be useful for
        initializing a Vivisect workspace with the extra "project" configuration
        values.

        Most of the standard vivbin command line options are not supported in this
        mode.  It is expected that either a valid existing workspace is specified,
        or a configuration file is specified that indicates the project-specific
        files and settings to use.
        """
        if parser is None:
            exename = os.path.basename(sys.modules['__main__'].__file__)
            parser = argparse.ArgumentParser(prog=exename)

        #parser.add_argument('-m', '--mode', default='emu', choices=['emu', 'interactive', 'analysis', 'test'],
        parser.add_argument('-m', '--mode', default='interactive', choices=['interactive', 'test'],
                            help='Emulator mode')
        parser.add_argument('-v', '--verbose', dest='verbose', default=1, action='count',
                            help='Enable verbose mode (multiples matter: -vvvv)')
        parser.add_argument('-c', '--config-dir', nargs='?', const=False,
                            help='Path to a directory to use for emulator configuration information')
        parser.add_argument('-O', '--option', default=None, action='append',
                            help='<secname>.<optname>=<optval> (optval must be json syntax)')
        parser.add_argument('-p', '--parser', dest='parsemod', default=None, action='store',
                            help='Manually specify the parser module (pe/elf/blob/...)')
        parser.add_argument('-E', '--entrypoint',
                            help='Specify Entry Point where the emulator should start execution')
        parser.add_argument('file', nargs='*')
        parsed_args = parser.parse_args(args)

        if defconfig is None:
            defconfig = {}

        if docconfig is None:
            docconfig = {}

        # Merge the defaults and docs provided with the class config
        defconfig = merge_dict(self.defconfig, defconfig)
        docconfig = merge_dict(self.docconfig, docconfig)

        # Merge the project options with the vivisect defaults
        defconfig = merge_dict(vivisect.defconfig, defconfig)
        docconfig = merge_dict(vivisect.docconfig, docconfig)

        if parsed_args.mode == 'emu':
            raise NotImplementedError('Fast emulator mode not yet supported, but coming soon!')
            #clicls = FastEmuCli
        elif parsed_args.mode == 'analysis':
            raise NotImplementedError('Analysis mode not yet supported, but coming soon! (although not as "soon" as fast emu mode)')
            #clicls = FastEmuCli
        else:
            # Use the standard vivisect CLI parsing class, this will return a
            # VivisectWorkspace when done.
            clicls = viv_cli.VivCli

        # If the config dir is not specified use the default project name instead of
        # the vivisect default ".viv/"
        if parsed_args.config_dir:
            configdir = parsed_args.config_dir
        elif parsed_args.config_dir is None:
            # find the default project dir by looking using the project name from
            # the configuration
            default_prj_dir = '.' + defconfig['project']['name']
            configdir = e_config.gethomedir(default_prj_dir, makedir=False)
        else:
            # If the "-c" option was provided but no path argument, set configdir
            # to None and then after the workspace is opened we will clear and
            # re-load the default configuration.
            #
            # TODO: Because we are still using the standard VivCli class here
            # instead of our own this is necessary because a VivsectWorkspace cannot
            # be opened without either specifying a configuration directory or using
            # the deault ~/.viv/ configuration directory.
            configdir = None

        if configdir is not None:
            # Make sure that the configuration directory is not the default vivisect
            # home ".viv"
            default_vivhome = e_config.gethomedir(".viv", makedir=False)
            if configdir == default_vivhome:
                raise Exception('Cannot use standard vivisect config in project mode')

            self.home = configdir

            # Parse the configuration
            cfgpath = os.path.join(self.home, 'viv.json')
        else:
            cfgpath = None
            self.home = None

        self.config = e_config.EnviConfig(filename=cfgpath, defaults=defconfig, docs=docconfig, autosave=False)

        # workspace used for file parsing
        # TODO: integrate VivWorkspace.MemoryObject behavior cleanly with 
        vw = clicls(confdir=None, autosave=False)

        # Save the mode
        # TODO: meta variables in project?
        vw.setTransMeta("ProjectMode", parsed_args.mode)

        # setup logging
        self.verbose = min(parsed_args.verbose, len(e_common.LOG_LEVELS)-1)
        level = e_common.LOG_LEVELS[self.verbose]
        e_common.initLogging(logger, level=level)
        logger.warning("LogLevel: %r  %r  %r", self.verbose, level, logging.getLevelName(level))

        # Parse any command-line options
        if parsed_args.option is not None:
            for option in parsed_args.option:
                if option in ('-h', '?'):
                    logger.critical(self.config.reprConfigPaths())
                    logger.critical("syntax: \t-O <secname>.<optname>=<optval> (optval must be json syntax)")
                    sys.exit(-1)

                try:
                    self.config.parseConfigOption(option)
                except e_exc.ConfigNoAssignment as e:
                    logger.critical(self.config.reprConfigPaths() + "\n")
                    logger.critical(e)
                    logger.critical("syntax: \t-O <secname>.<optname>=<optval> (optval must be json syntax)")
                    sys.exit(-1)

                except Exception as e:
                    logger.critical(self.config.reprConfigPaths())
                    logger.critical("With entry: %s", option)
                    logger.critical(e)
                    sys.exit(-1)

        for fname in parsed_args.file:
            start = time.time()
            # If the file provided is a .xcal or an ihex file force vivisect 
            # to use the xcal parser utility.
            if (parsed_args.parsemod is None and fname.lower().endswith('.xcal')) or \
                    parsed_args.parsemod == 'ihex':
                parsemod = 'xcal'
            else:
                parsemod = parsed_args.parsemod

            vw.loadFromFile(fname, fmtname=parsemod)

            end = time.time()
            logger.info('Loaded (%.4f sec) %s', (end - start), fname)

        # If an entry point was specified save it now.
        if parsed_args.entrypoint is not None:
            logger.info('Adding entrypoint %s', parsed_args.entrypoint)
            vw.addEntryPoint(int(parsed_args.entrypoint, 0))

        # If a workspace was not specified we need to manually set all of the
        # various Meta options based on project configuration options.
        if vw.getMeta('Architecture') is None:
            if self.config.project.arch == 'unknown':
                raise Exception('architecture must be defined')

            vw.setMeta('Architecture', self.config.project.arch)

        defaultcall = vw.getMeta('Platform')
        if defaultcall is None or defaultcall.lower() == 'unknown':
            vw.setMeta('DefaultCall', viv_const.archcalls.get(self.config.project.arch, 'unknown'))

        platform = vw.getMeta('Platform')
        if platform is None or platform.lower() == 'unknown':
            vw.setMeta('Platform', self.config.project.platform)

        # Always force it to use the project endianness
        vw.setMeta('bigend', self.config.project.bigend)

        # Save the workspace and parsed args
        self.vw = vw
        self.args = parsed_args

    def get_project_path(self, filename):
        """
        Helper function to return a full path to a file that should reside in
        the project directory unless the filename provided already is an
        absolute path the Helper.

        Project files would be in this directory by default:
            ~/.PROJECT/WORKSPACE/filename
        """
        if filename is None or self.home is None:
            return None
        elif filename.startswith(self.home):
            return os.path.relpath(filename, self.home)
        elif os.path.isabs(filename):
            return filename
        else:
            return os.path.normpath(os.path.join(self.home, filename))

    def get_project_config(self, path=None):
        if path is None:
            path = ''

        cfg = self.config
        for part in path.split('.'):
            if part in cfg.cfgsubsys:
                cfg = cfg.getSubConfig(part)
            elif part in cfg.cfginfo:
                # Should be the last item
                cfg = cfg.get(part)

        return cfg
