import shlex
from spotty.deployment.abstract_container_commands import AbstractContainerCommands
from spotty.helpers.cli import shlex_join


class DockerCommands(AbstractContainerCommands):

    def build(self, image_name: str) -> str:
        if not self._instance_config.dockerfile_path:
            raise ValueError('Cannot generate the "build" command as Dockerfile path is not specified')

        if not self._instance_config.docker_context_path:
            raise ValueError('Cannot generate the "build" command as Docker context path is not set')

        build_cmd = 'docker build -t %s -f %s %s' % (image_name, shlex.quote(self._instance_config.dockerfile_path),
                                                     shlex.quote(self._instance_config.docker_context_path))

        return build_cmd

    def run(self, image_name: str = None) -> str:
        image_name = image_name if image_name else self._instance_config.container_config.image

        # prepare "docker run" arguments
        args = ['-td', '--net=host'] + self._instance_config.container_config.runtime_parameters

        for volume_mount in self._instance_config.volume_mounts:
            args += ['-v', '%s:%s:%s' % (volume_mount.host_path, volume_mount.mount_path, volume_mount.mode)]

        for env_name, env_value in self._instance_config.container_config.env.items():
            args += ['-e', '%s=%s' % (env_name, env_value)]

        args += ['--name', self._instance_config.full_container_name]

        run_cmd = 'docker run $(nvidia-smi &> /dev/null && echo "--gpus all") %s %s /bin/sh > /dev/null' \
                  % (shlex_join(args), image_name)

        return run_cmd

    def is_created(self, container_name: str = None, is_running: bool = False) -> str:
        container_name = container_name if container_name else self._instance_config.full_container_name
        show_all = '' if is_running else 'a'

        test_cmd = '[ $(docker ps -q%s --filter name="%s" | wc -c) -ne 0 ]' % (show_all, container_name)

        return test_cmd

    def remove(self):
        return 'docker rm -f "%s" > /dev/null' % self._instance_config.full_container_name

    def exec(self, command: str, container_name: str = None, working_dir: str = None) -> str:
        container_name = container_name if container_name else self._instance_config.full_container_name
        working_dir = working_dir if working_dir else self._instance_config.container_config.working_dir

        exec_cmd = 'docker exec -it'
        if working_dir:
            exec_cmd += ' -w ' + working_dir

        exec_cmd += ' %s %s' % (container_name, command)

        # run "exec" command only if the container is running
        test_cmd = self.is_created(container_name, is_running=True)
        error_msg = 'Container is not running.\\nUse the "spotty start -C" command to start it.'
        cond_exec_cmd = 'if %s; then %s; else echo %s; exit 1; fi' % (test_cmd, exec_cmd, shlex.quote(error_msg))

        return cond_exec_cmd