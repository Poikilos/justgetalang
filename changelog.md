# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [git] - 2022-03-28
### Changed
- Change all CLI arguments to named arguments.
- Set langsPath to "." if an expected file is there.
- Rename `translationsKey` to `languagesKey`

### Added
- new CLI arguments `--from`, `--to`, `--extension`, `--dictionary`, `--languages-key`.
- Show the count of `origPack.keys` for clarity in case 0 were found (to indicate to the user that there is probably a problem).

### Fixed
