# gitlab-repository-exporter

Daemon to export info about branches and merge requests inside of repository.
Requires read-only access to gitlab api.

# Sample data

```code
# HELP branch_count number of branch in the project
# TYPE branch_count gauge
branch_count{project_url="https://gitlab.com/gitlab-course-public/my-static-website"} 214.0
# HELP branch_ttl detail info for branches in the project
# TYPE branch_ttl gauge
branch_ttl{branch_name="feat/blog",committer="john.@gmail.com",project_url="https://gitlab.com/gitlab-course-public/my-static-website"} 1.64571217e+012
```

```code
# HELP mr_count number of mrs in the project
# TYPE mr_count gauge
mr_count{project_url="https://gitlab.com/gitlab-course-public/my-static-website"} 9.0
# HELP mr_ttl detail info for mrs in the project
# TYPE mr_ttl gauge
mr_ttl{author="a.horbach",branch_name="feat/add-about",project_url="https://gitlab.com/gitlab-course-public/my-static-website/-/merge_requests/939",title="feat(about): add page",votes_diff="1"} 1.649081762e+012
```
# Roadmap

- [ ] - TODO status
- [ ] - example/kubernetes
