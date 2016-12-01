# coding: utf-8
# import datetime
import errno
import logging
import os
import sys
import subprocess

from errbot import BotPlugin, arg_botcmd
from errbot.utils import ValidationException, recurse_check_structure

logger = logging.getLogger(__file__)


class Merge(BotPlugin):  # pylint:disable=too-many-ancestors
    """Merge GitHub PRs your way.

    Allow for pull requests in a GitHub repo to be performed through Errbot, using a consistent strategy and prettier
    commit template.
    """

    def activate(self):
        if not self.config:
            # Don't allow activation until we are configured
            message = 'Merge is not configured, please do so.'
            self.log.info(message)
            self.warn_admins(message)
            return

        self.setup_repos()
        super().activate()

    def setup_repos(self):
        """Clone the projects in the configuration into the `REPOS_ROOT` if they do not exist already."""
        try:
            os.makedirs(self.config['REPOS_ROOT'])
        except OSError as exc:
            # If the error is that the directory already exists, we don't care about it
            if exc.errno != errno.EEXIST:
                raise exc

        for project_name in self.config['projects']:
            if not os.path.exists(os.path.join(self.config['REPOS_ROOT'], project_name)):
                # Possible race condition if folder somehow gets created between check and creation
                Merge.run_subprocess(
                    ['git', 'clone', self.config['projects'][project_name]['repo_url']],
                    cwd=self.config['REPOS_ROOT'],
                )

    def get_configuration_template(self) -> str:
        return {
            'REPOS_ROOT': '/home/web/repos/',
            'forbidden_branches': ['master', 'develop'],  # Can't merge these
            # 'MERGE_FLAGS': '--no-ff',
            # 'MERGE_COMMIT_TEMPLATE': '',
            'projects': {
                'some-project': {  # Name of the project in GitHub
                    'repo_url': 'git@github.com:netquity/some-project.git',
                    'github_org': 'netquity',
                },
            },
        }

    def check_configuration(self, configuration: 'typing.Mapping') -> None:
        """Allow for the `projects` key to have a variable number of definitions."""
        # Remove the `projects` key from both the template and the configuration and then test them separately
        try:
            config_template = self.get_configuration_template().copy()
            projects_template = config_template.pop('projects')
            projects_config = configuration.pop('projects')  # Might fail
        except KeyError:
            raise ValidationException(
                'Your configuration must include a projects key with at least one project configured.'
            )

        recurse_check_structure(config_template, configuration)

        # Check that each project configuration matches the template
        for k, v in projects_config.items():
            recurse_check_structure(projects_template['some-project'], v)

        configuration.update({'projects': projects_config})

    @arg_botcmd('--project-name', dest='project_name', type=str.lower, required=True)
    @arg_botcmd('--branch-name', dest='branch_name', type=str, required=True)
    def merge(
            self,
            msg: 'errbot.backends.base.Message',
            project_name: str,
            branch_name: str,
    ) -> str:
        """For the given project, merge the given branch to develop and push back to origin."""
        # TODO: validate project_name
        try:
            self.validate_branch(branch_name)
        except ValidationException as exc:
            failure_message = '%s is not a valid branch choice.' % branch_name
            self.log.exception(
                failure_message,
            )
            return self.send_card(
                in_reply_to=msg,
                body=failure_message,
                color='red',
            )

        # TODO: trap your exceptions!
        project_root = self.get_project_root(project_name)
        Merge.git_merge_branch_to_develop(project_root, branch_name)
        Merge.git_push_develop_to_origin(project_root)
        Merge.git_delete_branch(project_root, branch_name)

        return self.send_card(
            in_reply_to=msg,
            pretext='I was able to complete the %s merge for you.' % project_name,
            fields=(
                ('Receiver Branch', 'develop'),
                ('Giver Branch', branch_name),
            ),
            color='green',
        )

    def get_project_root(self, project_name: str) -> str:
        """Get the root of the project's Git repo locally."""
        return self.config['REPOS_ROOT'] + project_name

    def validate_branch(self, branch_name: str):
        """Check that the given branch is not on the list of forbidden branches."""
        if branch_name in self.config['forbidden_branches']:
            raise ValidationException(
                '{} are forbidden choices for --branch-name.'.format(
                    ', '.join(str(branch) for branch in self.config['forbidden_branches'])
                )
            )

    @staticmethod
    def git_merge_branch_to_develop(project_root: str, branch_name: str):  # TODO: accept commit hash?
        """Merge the given branch into develop."""
        for argv in [
                ['fetch', '-p'],
                ['checkout', '-B', 'develop', 'origin/develop'],
                ['merge', '--no-ff', '-m', 'Merge {} to develop'.format(branch_name), 'origin/{}'.format(branch_name)],
                ['push', 'origin', 'develop'],
        ]:
            Merge.run_subprocess(
                ['git'] + argv,
                cwd=project_root,
            )

    @staticmethod
    def git_push_develop_to_origin(project_root: str):
        """Push the develop branch for the given project back to origin."""
        Merge.run_subprocess(
            ['git', 'push', 'origin', 'develop'],
            cwd=project_root,
        )

    @staticmethod
    def git_delete_branch(project_root: str, branch_name: str):
        for argv in [
                ['push', 'origin', '--delete', '{}'.format(branch_name)],
                ['branch', '-D', '{}'.format(branch_name)],
        ]:
            Merge.run_subprocess(
                ['git'] + argv,
                cwd=project_root,
            )

    @staticmethod
    def run_subprocess(args: list, cwd: str=None):
        """Run the local command described by `args` with some defaults applied."""
        return subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine out/err into stdout; stderr will be None
            universal_newlines=True,
            check=True,
            cwd=cwd,
        )
