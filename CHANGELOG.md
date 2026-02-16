# Changelog

## [v1.5.0] - 2026-02-15
### Added
- **Dependency Management**: Added `package.json` and Vite configuration for the frontend.
- **Code Refinement**: Standardized logging and error handling in `bridge.py` and `print_phomemo.py`.
- **Frontend Adjustment**: Aligning the frontend with the project's artistic goal.

### Changed
- **File Structure**: Organized assets in `barzar/assets/` and cleaned up redundant temporary files in `png/`.

## [v1.0.0] - 2026-02-11
- **New README**: Fixed some screw-ups..

## [v1.0.0] - 2026-02-11
### Added
- **Security and Privacy**: All sensitive configurations (URLs, keys) are now loaded from environment variables (`.env`), eliminating hardcoded data.
- **Portability**: Scripts now automatically detect the project root directory, allowing execution from any location or user via `start_barzar.sh`.
- **Simplified Configuration**: New `.env.example` file and updated documentation to facilitate initial setup.
- **Direct Phomemo Connection**: Optional support for `BLE_PRINTER_ADDRESS` in `.env` to skip scanning and connect instantly to the printer.
- **Robustness Fixes**: Scripts now automatically create necessary folders (`temp`, `uploads`, `png`) if they don't exist, preventing crashes.

### Changed
- **Relative Paths**: Complete replacement of absolute paths with relative ones in all modules (`server.py`, `bridge.py`, `start_barzar.sh`).
- **Configurable Frontend**: API URL extracted to a configuration variable at the top of `index.html`.

## [v0.5.0] - 2026-02-11
### Added
- **Heartbeat System**: Implemented a heartbeat signal every 30 seconds to keep the Bluetooth connection active and prevent the Phomemo T02 from entering standby mode.
- **Status Synchronization**: "Ready" and "Telepathy done" status messages are now consistent between the local bridge and the remote server.
- **Overlay Anchoring**: Refined anchoring of `cingarro.png` to align precisely with the mouth landmark.
- **Task Visualization**: Integration with task management for better development tracking.

## [v0.4.0] - 2026-02-10
### Added
- **Automated Workflow**: Created `start_barzar.sh` script to launch Server, Tunnel, Printer Monitor, and Bridge in separate terminal windows.
- **Dynamic Font Scaling**: Text messages now automatically adjust font size to fit perfectly within the frame.

## [v0.3.0] - 2026-02-10
### Added
- **Apple Vision Integration**: Facial landmark detection implemented in `bridge.py` using the native macOS framework.
- **Dynamic Overlays**: Automatic application of random items (glasses, sparkles, kittens, frames) based on detected face points and background contrast.
- **SIPS Integration**: Image processing optimization using the macOS `sips` tool to ensure DPI and format compatibility.

## [v0.2.0] - 2026-02-10
### Added
- **Hybrid Architecture**: Established "Telepathy" flow: Frontend (Web) -> Cloudflare Tunnel -> Flask Server -> Local Bridge -> Printer.
- **Cloudflare Tunnel**: Secure communication between remote and local for the thermal printing pipeline.
- **Polling System**: Implemented logic to fetch pending content from the remote server.

## [v0.1.0] - 2026-02-09
### Added
- **Initial Frontend**: Responsive web interface for photo capture and text message sending.
- **Core Server**: Basic Flask implementation for file upload and status management.
- **Logo and Identity**: Visual assets for the "Barzar" identity.
