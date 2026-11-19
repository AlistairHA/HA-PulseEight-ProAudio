/* Pulse-Eight neo video matrix control panel for Home Assistant (neo:X, neo:X+ ...).
 * Shares its design and interaction model with the ProAudio panel.
 * Dependency-free web component. Registered as a sidebar panel by the
 * integration, and also usable as a dashboard card:
 *   type: custom:neo-matrix-card   (optional: entry_id, tab: routing|outputs|hdbt|presets|system|settings)
 */
const ICONS = {"thermo":"M15 13V5A3 3 0 0 0 9 5V13A5 5 0 1 0 15 13M12 4A1 1 0 0 1 13 5V8H11V5A1 1 0 0 1 12 4Z","tv":"M21,17H3V5H21M21,3H3A2,2 0 0,0 1,5V17A2,2 0 0,0 3,19H8V21H16V19H21A2,2 0 0,0 23,17V5A2,2 0 0,0 21,3Z","voldown":"M3,9H7L12,4V20L7,15H3V9M14,11H22V13H14V11Z","video":"M17,10.5V7A1,1 0 0,0 16,6H4A1,1 0 0,0 3,7V17A1,1 0 0,0 4,18H16A1,1 0 0,0 17,17V13.5L21,17.5V6.5L17,10.5Z","ethernet":"M7,15H9V18H11V15H13V18H15V15H17V18H19V9H15V6H9V9H5V18H7V15M4.38,3H19.63C20.94,3 22,4.06 22,5.38V19.63A2.37,2.37 0 0,1 19.63,22H4.38C3.06,22 2,20.94 2,19.63V5.38C2,4.06 3.06,3 4.38,3Z","hdmi":"M18,7V4A2,2 0 0,0 16,2H8A2,2 0 0,0 6,4V7H5V13L8,19V22H16V19L19,13V7H18M8,4H16V7H14V5H13V7H11V5H10V7H8V4Z","chevron":"M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z","group":"M17,16H15V22H12V17H8V22H5V16H3L10,10L17,16M6,2L10,6H9V9H7V6H5V9H3V6H2L6,2M18,3L23,8H22V12H19V9H17V12H15.34L14,10.87V8H13L18,3Z","up":"M13,20H11V8L5.5,13.5L4.08,12.08L12,4.16L19.92,12.08L18.5,13.5L13,8V20Z","down":"M11,4H13V16L18.5,10.5L19.92,11.92L12,19.84L4.08,11.92L5.5,10.5L11,16V4Z","undo":"M12.5,8C9.85,8 7.45,9 5.6,10.6L2,7V16H11L7.38,12.38C8.77,11.22 10.54,10.5 12.5,10.5C16.04,10.5 19.05,12.81 20.1,16L22.47,15.22C21.08,11.03 17.15,8 12.5,8Z","power":"M16.56,5.44L15.11,6.89C16.84,7.94 18,9.83 18,12A6,6 0 0,1 12,18A6,6 0 0,1 6,12C6,9.83 7.16,7.94 8.88,6.88L7.44,5.44C5.36,6.88 4,9.28 4,12A8,8 0 0,0 12,20A8,8 0 0,0 20,12C20,9.28 18.64,6.88 16.56,5.44M13,3H11V13H13","volume":"M14,3.23V5.29C16.89,6.15 19,8.83 19,12C19,15.17 16.89,17.84 14,18.7V20.77C18,19.86 21,16.28 21,12C21,7.72 18,4.14 14,3.23M16.5,12C16.5,10.23 15.5,8.71 14,7.97V16C15.5,15.29 16.5,13.76 16.5,12M3,9V15H7L12,20V4L7,9H3Z","mute":"M12,4L9.91,6.09L12,8.18M4.27,3L3,4.27L7.73,9H3V15H7L12,20V13.27L16.25,17.53C15.58,18.04 14.83,18.46 14,18.7V20.77C15.38,20.45 16.63,19.82 17.68,18.96L19.73,21L21,19.73L12,10.73M19,12C19,12.94 18.8,13.82 18.46,14.64L19.97,16.15C20.62,14.91 21,13.5 21,12C21,7.72 18,4.14 14,3.23V5.29C16.89,6.15 19,8.83 19,12M16.5,12C16.5,10.23 15.5,8.71 14,7.97V10.18L16.45,12.63C16.5,12.43 16.5,12.21 16.5,12Z","unlink":"M2,5.27L3.28,4L20,20.72L18.73,22L13.9,17.17L11.29,19.78C9.34,21.73 6.17,21.73 4.22,19.78C2.27,17.83 2.27,14.66 4.22,12.71L5.71,11.22C5.7,12.04 5.83,12.86 6.11,13.65L5.64,14.12C4.46,15.29 4.46,17.19 5.64,18.36C6.81,19.54 8.71,19.54 9.88,18.36L12.5,15.76L10.88,14.15C10.87,14.39 10.77,14.64 10.59,14.83C10.2,15.22 9.56,15.22 9.17,14.83C8.12,13.77 7.63,12.37 7.72,11L2,5.27M12.71,4.22C14.66,2.27 17.83,2.27 19.78,4.22C21.73,6.17 21.73,9.34 19.78,11.29L18.29,12.78C18.3,11.96 18.17,11.14 17.89,10.36L18.36,9.88C19.54,8.71 19.54,6.81 18.36,5.64C17.19,4.46 15.29,4.46 14.12,5.64L10.79,8.97L9.38,7.55L12.71,4.22M13.41,9.17C13.8,8.78 14.44,8.78 14.83,9.17C16.2,10.54 16.61,12.5 16.06,14.23L14.28,12.46C14.23,11.78 13.94,11.11 13.41,10.59C13,10.2 13,9.56 13.41,9.17Z","refresh":"M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z","edit":"M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z","del":"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z","plus":"M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z","menu":"M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z","check":"M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z","close":"M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z","play":"M10,16.5V7.5L16,12M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z","speaker":"M12,12A3,3 0 0,0 9,15A3,3 0 0,0 12,18A3,3 0 0,0 15,15A3,3 0 0,0 12,12M12,20A5,5 0 0,1 7,15A5,5 0 0,1 12,10A5,5 0 0,1 17,15A5,5 0 0,1 12,20M12,4A2,2 0 0,1 14,6A2,2 0 0,1 12,8C10.89,8 10,7.1 10,6C10,4.89 10.89,4 12,4M17,2H7C5.89,2 5,2.89 5,4V20A2,2 0 0,0 7,22H17A2,2 0 0,0 19,20V4C19,2.89 18.1,2 17,2Z","input":"M11 6V12H5V6H7V2C7 1.45 7.45 1 8 1S9 1.45 9 2V6H11M5 14V16C5 17.3 5.84 18.4 7 18.82V23H9V18.82C10.16 18.4 11 17.3 11 16V14H5M17 6V2C17 1.45 16.55 1 16 1S15 1.45 15 2V6H13V12H19V6H17M13 14V16C13 17.3 13.84 18.4 15 18.82V23H17V18.82C18.16 18.4 19 17.3 19 16V14H13Z","coax":"M7.05 3.5C5.68 4.88 5.68 7.1 7.05 8.47L15.54 16.95C16.12 17.54 16.12 18.5 15.54 19.07C14.95 19.66 14 19.66 13.41 19.07L9.17 14.83L10.23 13.77L6.7 10.23L6.34 10.59L4.93 9.17C4.54 8.78 3.91 8.78 3.5 9.17L2.1 10.59C1.71 11 1.71 11.61 2.1 12L3.5 13.41L3.16 13.77L6.7 17.3L7.76 16.24L12 20.5C13.37 21.85 15.58 21.85 16.95 20.5C18.32 19.12 18.32 16.9 16.95 15.54L8.46 7.05C7.88 6.46 7.88 5.5 8.46 4.93C9.05 4.34 10 4.34 10.59 4.93L14.83 9.17L13.77 10.23L17.3 13.77L17.66 13.41L19.07 14.83C19.46 15.22 20.1 15.22 20.5 14.83L21.9 13.41C22.29 13 22.29 12.39 21.9 12L20.5 10.59L20.84 10.23L17.3 6.7L16.24 7.76L12 3.5C10.63 2.15 8.42 2.15 7.05 3.5M2.81 11.29L4.22 9.88L5.64 11.29L4.22 12.71M18.36 12.71L19.78 11.29L21.19 12.71L19.78 14.12Z","optical":"M6,3H3V6A3,3 0 0,0 6,3M14,3H12A9,9 0 0,1 3,12V14C9.08,14 14,9.07 14,3M10,3H8A5,5 0 0,1 3,8V10A7,7 0 0,0 10,3M10,21H12A9,9 0 0,1 21,12V10A11,11 0 0,0 10,21M18,21H21V18A3,3 0 0,0 18,21M14,21H16A5,5 0 0,1 21,16V14A7,7 0 0,0 14,21Z","alert":"M13,13H11V7H13M13,17H11V15H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z","lan":"M10,2C8.89,2 8,2.89 8,4V7C8,8.11 8.89,9 10,9H11V11H2V13H6V15H5C3.89,15 3,15.89 3,17V20C3,21.11 3.89,22 5,22H9C10.11,22 11,21.11 11,20V17C11,15.89 10.11,15 9,15H8V13H16V15H15C13.89,15 13,15.89 13,17V20C13,21.11 13.89,22 15,22H19C20.11,22 21,21.11 21,20V17C21,15.89 20.11,15 19,15H18V13H22V11H13V9H14C15.11,9 16,8.11 16,7V4C16,2.89 15.11,2 14,2H10M10,4H14V7H10V4M5,17H9V20H5V17M15,17H19V20H15V17Z","info":"M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z","select":"M9,9H15V15H9M7,17H17V7H7M15,5H17V3H15M15,21H17V19H15M19,17H21V15H19M19,9H21V7H19M19,21A2,2 0 0,0 21,19H19M19,13H21V11H19M11,21H13V19H11M9,3H7V5H9M3,17H5V15H3M5,21V19H3A2,2 0 0,0 5,21M19,3V5H21A2,2 0 0,0 19,3M13,3H11V5H13M3,9H5V7H3M7,21H9V19H7M3,13H5V11H3M3,5H5V3A2,2 0 0,0 3,5Z","lock":"M12,17A2,2 0 0,0 14,15C14,13.89 13.1,13 12,13A2,2 0 0,0 10,15A2,2 0 0,0 12,17M18,8A2,2 0 0,1 20,10V20A2,2 0 0,1 18,22H6A2,2 0 0,1 4,20V10C4,8.89 4.9,8 6,8H7V6A5,5 0 0,1 12,1A5,5 0 0,1 17,6V8H18M12,3A3,3 0 0,0 9,6V8H15V6A3,3 0 0,0 12,3Z","eye":"M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z","eyeoff":"M11.83,9L15,12.16C15,12.11 15,12.05 15,12A3,3 0 0,0 12,9C11.94,9 11.89,9 11.83,9M7.53,9.8L9.08,11.35C9.03,11.56 9,11.77 9,12A3,3 0 0,0 12,15C12.22,15 12.44,14.97 12.65,14.92L14.2,16.47C13.53,16.8 12.79,17 12,17A5,5 0 0,1 7,12C7,11.21 7.2,10.47 7.53,9.8M2,4.27L4.28,6.55L4.73,7C3.08,8.3 1.78,10 1,12C2.73,16.39 7,19.5 12,19.5C13.55,19.5 15.03,19.2 16.38,18.66L16.81,19.08L19.73,22L21,20.73L3.27,3M12,7A5,5 0 0,1 17,12C17,12.64 16.87,13.26 16.64,13.82L19.57,16.75C21.07,15.5 22.27,13.86 23,12C21.27,7.61 17,4.5 12,4.5C10.6,4.5 9.26,4.75 8,5.2L10.17,7.35C10.74,7.13 11.35,7 12,7Z","capture":"M20,4H16.83L15,2H9L7.17,4H4A2,2 0 0,0 2,6V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V6A2,2 0 0,0 20,4M20,18H4V6H8.05L9.88,4H14.12L15.95,6H20V18M12,7A5,5 0 0,0 7,12A5,5 0 0,0 12,17A5,5 0 0,0 17,12A5,5 0 0,0 12,7M12,15A3,3 0 0,1 9,12A3,3 0 0,1 12,9A3,3 0 0,1 15,12A3,3 0 0,1 12,15Z","signal":"M16.5,21C13.5,21 12.31,16.76 11.05,12.28C10.14,9.04 9,5 7.5,5C4.11,5 4,11.93 4,12H2C2,11.63 2.06,3 7.5,3C10.5,3 11.71,7.25 12.97,11.74C13.83,14.8 15,19 16.5,19C19.94,19 20.03,12.07 20.03,12H22.03C22.03,12.37 21.97,21 16.5,21Z","matrix":"M18,11H14.82C14.4,9.84 13.3,9 12,9C10.7,9 9.6,9.84 9.18,11H6C5.67,11 4,10.9 4,9V8C4,6.17 5.54,6 6,6H16.18C16.6,7.16 17.7,8 19,8A3,3 0 0,0 22,5A3,3 0 0,0 19,2C17.7,2 16.6,2.84 16.18,4H6C4.39,4 2,5.06 2,8V9C2,11.94 4.39,13 6,13H9.18C9.6,14.16 10.7,15 12,15C13.3,15 14.4,14.16 14.82,13H18C18.33,13 20,13.1 20,15V16C20,17.83 18.46,18 18,18H7.82C7.4,16.84 6.3,16 5,16A3,3 0 0,0 2,19A3,3 0 0,0 5,22C6.3,22 7.4,21.16 7.82,20H18C19.61,20 22,18.93 22,16V15C22,12.07 19.61,11 18,11M19,4A1,1 0 0,1 20,5A1,1 0 0,1 19,6A1,1 0 0,1 18,5A1,1 0 0,1 19,4M5,20A1,1 0 0,1 4,19A1,1 0 0,1 5,18A1,1 0 0,1 6,19A1,1 0 0,1 5,20Z","tune":"M3,17V19H9V17H3M3,5V7H13V5H3M13,21V19H21V17H13V15H11V21H13M7,9V11H3V13H7V15H9V9H7M21,13V11H11V13H21M15,9H17V7H21V5H17V3H15V9Z","star":"M16.23,18L12,15.45L7.77,18L8.89,13.19L5.16,9.96L10.08,9.54L12,5L13.92,9.53L18.84,9.95L15.11,13.18L16.23,18M12,2C6.47,2 2,6.5 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z","cog":"M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.21,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.21,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.67 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z","pulse":"M7.5,4A5.5,5.5 0 0,0 2,9.5C2,10 2.09,10.5 2.22,11H6.3L7.57,7.63C7.87,6.83 9.05,6.75 9.43,7.63L11.5,13L12.09,11.58C12.22,11.25 12.57,11 13,11H21.78C21.91,10.5 22,10 22,9.5A5.5,5.5 0 0,0 16.5,4C14.64,4 13,4.93 12,6.34C11,4.93 9.36,4 7.5,4V4M3,12.5A1,1 0 0,0 2,13.5A1,1 0 0,0 3,14.5H5.44L11,20C12,20.9 12,20.9 13,20L18.56,14.5H21A1,1 0 0,0 22,13.5A1,1 0 0,0 21,12.5H13.4L12.47,14.8C12.07,15.81 10.92,15.67 10.55,14.83L8.5,9.5L7.54,11.83C7.39,12.21 7.05,12.5 6.6,12.5H3Z"};
const DOMAIN = "pulse_eight_neo";
const PALETTE = ["#4e79a7","#f28e2b","#59a14f","#e15759","#b07aa1","#76b7b2","#edc948","#ff9da7",
  "#9c755f","#2f9e8f","#d37295","#8cd17d","#a0cbe8","#ffbe7d","#86bcb6","#f1ce63"];
const SIGNAL = { signal: ["Signal", "ok"], no_signal: ["No signal", "warn"] };
const TABS = [["routing", "Routing", "matrix"], ["outputs", "Outputs", "tv"], ["hdbt", "HDBaseT", "ethernet"], ["presets", "Presets", "star"],
  ["system", "System", "pulse"], ["settings", "Settings", "cog"]];

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const icon = (n, cls = "") => `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="${ICONS[n] || ""}"/></svg>`;
const dbLabel = (raw) => raw == null ? "–" : raw <= 0 ? "Mute" : `${((raw - 200) / 2).toFixed(1)} dB`;
const kindShort = { analog: "A", coax: "C", optical: "O" };
const ago = (t, now) => { if (!t) return "never"; const s = Math.max(0, Math.round(now - t)); return s < 60 ? `${s}s ago` : s < 3600 ? `${Math.round(s / 60)}m ago` : `${Math.round(s / 3600)}h ago`; };

class NeoApp extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._tab = "routing";
    this._layer = "video";
    this._sendTo = null;
    this._sel = new Set();
    this._filter = "visible";
    this._showHidden = false;
    this._drafts = null;        // settings edits
    this._editor = null;        // preset being edited
    this._modal = null;
    this._toast = null;
    this._busy = false;
    this._data = null;
    this._units = [];
    this._entry = null;
    this._unsub = null;
    this._renderPending = false;
    this._interacting = false;
    this._config = {};
    this.shadowRoot.addEventListener("click", (e) => this._onClick(e).catch(() => {}));
    this.shadowRoot.addEventListener("change", (e) => this._onChange(e).catch(() => {}));
    this.shadowRoot.addEventListener("input", (e) => this._onInput(e));
    this.shadowRoot.addEventListener("pointerdown", (e) => this._onPointerDown(e));
    this.shadowRoot.addEventListener("focusin", () => { if (!this._rendering) this._interacting = true; });
    this.shadowRoot.addEventListener("focusout", () => {
      // innerHTML replacement during our own render also fires focusout: ignore it
      if (this._rendering) return;
      const wasBlocking = this._interacting && (this._tab === "settings" || this._editor);
      this._interacting = false;
      if (wasBlocking) this._scheduleRender();
    });
    this._ro = new ResizeObserver(() => this._drawLines());
  }

  /* ---------- HA plumbing ---------- */
  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._start();
  }
  get hass() { return this._hass; }
  set narrow(v) { this._narrow = v; this._scheduleRender(); }
  set panel(p) { this._panel = p; }
  setConfig(cfg) { this._config = cfg || {}; if (cfg && cfg.tab) this._tab = cfg.tab; this._isCard = true; }
  getCardSize() { return 12; }
  static getStubConfig() { return { tab: "routing" }; }

  connectedCallback() {
    if (this._hass && !this._unsub && this._entry) this._subscribe();
    this._clock = setInterval(() => { if (this._tab === "status") this._scheduleRender(); }, 5000);
  }
  disconnectedCallback() {
    if (this._unsub) { this._unsub.then((u) => u && u()).catch(() => {}); this._unsub = null; }
    clearInterval(this._clock);
    this._ro.disconnect();
  }

  get _isAdmin() { return !this._hass || !this._hass.user || this._hass.user.is_admin; }

  async _start() {
    try {
      this._units = await this._hass.callWS({ type: `${DOMAIN}/list_units` });
    } catch (e) {
      this._error = `Could not load neo matrices: ${e.message || e}`;
      this._render();
      return;
    }
    if (!this._units.length) { this._error = "No neo matrix is configured. Add one under Settings → Devices & services → Pulse-Eight neo Matrix."; this._render(); return; }
    const wanted = this._config.entry_id;
    this._entry = (this._units.find((u) => u.entry_id === wanted) || this._units[0]).entry_id;
    this._subscribe();
  }

  _subscribe() {
    if (this._unsub) this._unsub.then((u) => u && u()).catch(() => {});
    this._data = null;
    this._render();
    this._unsub = this._hass.connection.subscribeMessage((snap) => {
      this._data = snap;
      this._recvAt = Date.now();
      this._scheduleRender();
    }, { type: `${DOMAIN}/subscribe`, entry_id: this._entry });
  }

  async _ws(type, payload = {}, okMsg) {
    try {
      const r = await this._hass.callWS({ type: `${DOMAIN}/${type}`, entry_id: this._entry, ...payload });
      if (okMsg) this._showToast(okMsg);
      return r;
    } catch (e) {
      this._showToast(e.message || String(e), true);
      throw e;
    }
  }

  _showToast(msg, error = false, undo = null) {
    this._toast = { msg, error, undo };
    clearTimeout(this._toastT);
    this._toastT = setTimeout(() => { this._toast = null; this._renderToast(); }, undo ? 9000 : error ? 6000 : 2500);
    this._renderToast();
  }

  /* ---------- rendering ---------- */
  _scheduleRender() {
    if (this._renderPending) return;
    this._renderPending = true;
    requestAnimationFrame(() => {
      this._renderPending = false;
      if (this._drag || this._sliding) { this._scheduleRenderLater(); return; }
      if (this._interacting && (this._tab === "settings" || this._editor)) { return; }
      this._render();
    });
  }
  _scheduleRenderLater() { clearTimeout(this._laterT); this._laterT = setTimeout(() => this._scheduleRender(), 150); }

  _colorFor(source) {
    if (!this._data || !source) return "var(--disabled-text-color, #999)";
    // Colour by position among the inputs the user has chosen to show, so the
    // handful of named sources always get distinct colours.
    if (this._colorKey !== this._data) {
      this._colorKey = this._data;
      this._colors = new Map();
      const shown = this._data.inputs.filter((i) => !i.hidden);
      const rest = this._data.inputs.filter((i) => i.hidden);
      [...shown, ...rest].forEach((i, n) => this._colors.set(i.source, PALETTE[n % PALETTE.length]));
    }
    return this._colors.get(source) || PALETTE[source % PALETTE.length];
  }
  _input(source) { return this._data && this._data.inputs.find((i) => i.source === source); }

  /* per-browser view preferences */
  _pref(key, def) { try { const v = localStorage.getItem(`neo-panel:${key}`); return v == null ? def : JSON.parse(v); } catch (e) { return def; } }
  _setPref(key, v) { try { localStorage.setItem(`neo-panel:${key}`, JSON.stringify(v)); } catch (e) { /* ignore */ } }
  get _compact() { const p = this._pref("compact", null); return p == null ? !!this._narrow : p; }
  get _collapsed() { if (!this._collapsedSet) this._collapsedSet = new Set(this._pref("collapsed", [])); return this._collapsedSet; }

  _render() {
    const scroller = this.shadowRoot.querySelector(".content");
    const scrollTop = scroller ? scroller.scrollTop : 0;
    // remember focus (e.g. the zone search box) across re-renders
    const ae = this.shadowRoot.activeElement;
    const focusSel = ae && ae.dataset && ae.dataset.c ? `[data-c="${ae.dataset.c}"]${ae.dataset.zone ? `[data-zone="${ae.dataset.zone}"]` : ""}${ae.dataset.src ? `[data-src="${ae.dataset.src}"]` : ""}${ae.dataset.group ? `[data-group="${ae.dataset.group}"]` : ""}` : null;
    const caret = ae && typeof ae.selectionStart === "number" ? [ae.selectionStart, ae.selectionEnd] : null;
    const d = this._data;
    let body;
    if (this._error) body = `<div class="empty">${icon("alert", "big")}<p>${esc(this._error)}</p></div>`;
    else if (!d) body = `<div class="empty"><div class="spinner"></div><p>Connecting to the matrix…</p></div>`;
    else body = this[`_tab_${this._tab}`]();
    this._rendering = true;
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <div class="app ${this._narrow ? "narrow" : ""} ${this._isCard ? "card" : ""}">
        ${this._header()}
        <div class="content">${!d || d.connected ? "" : `<div class="banner err">${icon("alert")} ${d.auth_error ? `The matrix rejected the admin password. Update it under Settings → Devices & services → neo Matrix → Reconfigure.` : `Not connected to ${esc(d.host)} — retrying…`}</div>`}
          ${body}</div>
        ${this._modalHtml()}
        <div class="toast-host"></div>
      </div>`;
    const sc = this.shadowRoot.querySelector(".content");
    if (sc) {
      sc.scrollTop = scrollTop;
      // inputs column is sticky, so lines must follow the scroll position
      const redraw = () => {
        if (this._tab !== "routing" || this._linesRaf) return;
        this._linesRaf = requestAnimationFrame(() => { this._linesRaf = null; this._drawLines(); });
      };
      sc.addEventListener("scroll", redraw, { passive: true });
      const ic = this.shadowRoot.querySelector(".col.inputs");
      if (ic) ic.addEventListener("scroll", redraw, { passive: true });
    }
    if (focusSel) {
      const el = this.shadowRoot.querySelector(focusSel);
      if (el) { el.focus(); if (caret && el.setSelectionRange) try { el.setSelectionRange(caret[0], caret[1]); } catch (e) { /* not a text input */ } }
    }
    this._rendering = false;
    this._renderToast();
    if (this._tab === "routing" && d) {
      const area = this.shadowRoot.querySelector(".matrix");
      if (area) {
        this._ro.disconnect(); this._ro.observe(area);
        // keep the sticky inputs column just below the (sticky) selection bar
        const sb = this.shadowRoot.querySelector(".selbar");
        area.style.setProperty("--sticky-top", sb ? `${sb.offsetHeight - 8}px` : "0px");
      }
      requestAnimationFrame(() => this._drawLines());
    }
  }

  _renderToast() {
    const host = this.shadowRoot.querySelector(".toast-host");
    if (!host) return;
    const t = this._toast;
    host.innerHTML = t ? `<div class="toast ${t.error ? "error" : ""}"><span>${esc(t.msg)}</span>${t.undo ? `<button class="toast-btn" data-a="undo">Undo</button>` : ""}</div>` : "";
  }


  /* ---------- Routing tab ---------- */



  /* ---------- groups / filters ---------- */

  /** Split outputs into the user's zone groups (+ "Other zones"). Returns null when no groups are defined. */
  _groupsView(outs) {
    const groups = (this._data.groups || []);
    if (!groups.length) return null;
    const byZone = new Map(outs.map((o) => [o.zone, o]));
    const used = new Set();
    const view = groups.map((g) => {
      const zones = g.zones.map((z) => byZone.get(z)).filter(Boolean);
      zones.forEach((o) => used.add(o.zone));
      return { id: g.id, name: g.name, zones };
    });
    const other = outs.filter((o) => !used.has(o.zone));
    if (other.length) view.push({ id: "_other", name: "Other zones", zones: other });
    return view.filter((g) => g.zones.length);
  }

  _isCollapsed(id) { return this._collapsed.has(id) && !(this._search || "").trim() && (this._outFilter || "all") === "all"; }
  _toggleCollapsed(id) {
    this._collapsed.has(id) ? this._collapsed.delete(id) : this._collapsed.add(id);
    this._setPref("collapsed", [...this._collapsed]);
    this._render();
  }

  _groupHead(g, kind = "routing") {
    const collapsed = this._isCollapsed(g.id);
    const routed = g.zones.filter((o) => o.source).length, on = g.zones.filter((o) => o.power).length;
    const allSel = g.zones.every((o) => this._sel.has(o.zone));
    const srcs = [...new Set(g.zones.map((o) => o.source).filter(Boolean))];
    const zs = g.zones.map((o) => o.zone).join(",");
    const actions = kind === "zones" ? `<span class="grp-acts">
        <button class="btn small ghost" data-a="grp-power" data-zones="${zs}" data-on="1">${icon("power")}On</button>
        <button class="btn small ghost" data-a="grp-power" data-zones="${zs}" data-on="0">Standby</button></span>` : "";
    return `<div class="grp-head ${collapsed ? "collapsed" : ""} ${allSel ? "selected" : ""}" data-group="${g.id}" data-zones="${zs}">
      <button class="sel-box btnlike" data-a="sel-group" data-zones="${zs}" title="Select group">${allSel ? icon("check") : ""}</button>
      <button class="caret" data-a="toggle-group" data-group="${g.id}" title="${collapsed ? "Expand" : "Collapse"}">${icon("chevron")}</button>
      <span class="nm">${esc(g.name)}</span>
      <span class="grp-stats">${on}/${g.zones.length} displays on</span>
      <span class="spacer"></span>
      <span class="grp-dots">${srcs.slice(0, 6).map((s) => `<span class="dot" title="${esc((this._input(s) || {}).name || "")}" style="--c:${this._colorFor(s)}"></span>`).join("")}</span>
      ${actions}
    </div>`;
  }




  _drawLines() {
    const area = this.shadowRoot.querySelector(".matrix");
    const svg = this.shadowRoot.querySelector("svg.lines");
    if (!area || !svg || !this._data) return;
    const base = area.getBoundingClientRect();
    svg.setAttribute("width", area.scrollWidth);
    svg.setAttribute("height", area.scrollHeight);
    const paths = [], seen = new Set();
    for (const o of this._filteredOutputs()) {
      if (!o.source) continue;
      const inEl = area.querySelector(`.in-card[data-src="${o.source}"]`);
      // zone inside a collapsed group: draw one line to the group header instead
      let outEl = area.querySelector(`.out-card[data-zone="${o.zone}"]`), key = `z${o.zone}`;
      if (!outEl) {
        const head = [...area.querySelectorAll(".grp-head.collapsed")].find((h) => h.dataset.zones.split(",").includes(String(o.zone)));
        if (!head) continue;
        outEl = head; key = `g${head.dataset.group}:${o.source}`;
      }
      if (!inEl || seen.has(key)) continue;
      seen.add(key);
      const a = inEl.getBoundingClientRect(), b = outEl.getBoundingClientRect();
      const x1 = a.right - base.left, y1 = a.top + a.height / 2 - base.top;
      const x2 = b.left - base.left, y2 = b.top + b.height / 2 - base.top;
      const dx = Math.max(30, (x2 - x1) / 2);
      const sel = this._sel.has(o.zone);
      paths.push(`<path d="M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}" stroke="${this._colorFor(o.source)}" class="${sel ? "sel" : ""} ${o.power === false ? "off" : ""} ${key[0] === "g" ? "grp" : ""}"/>`);
    }
    svg.innerHTML = paths.join("");
  }

  /* ---------- Zones tab ---------- */


  /* ---------- Presets tab ---------- */


  /* ---------- Status tab ---------- */

  /* ---------- Settings tab ---------- */


  /* ---------- modal ---------- */
  _confirm(title, text, ok, danger, fn) { this._modal = { title, text, ok, danger, fn }; this._render(); }

  /* ---------- events ---------- */

  _header() {
    const d = this._data;
    const units = this._units.length > 1
      ? `<select class="unit-select" data-c="unit">${this._units.map((u) => `<option value="${u.entry_id}" ${u.entry_id === this._entry ? "selected" : ""}>${esc(u.title)}</option>`).join("")}</select>`
      : `<span class="title">${esc(d ? d.title : "neo matrix")}</span>`;
    const conn = d ? `<span class="pill ${d.connected ? "ok" : "err"}">${d.connected ? "Connected" : d.auth_error ? "Password needed" : "Offline"}</span>` : "";
    const health = d && d.status_message ? `<span class="hdr-status ${/health|ok/i.test(d.status_message) ? "ok" : "warn"}">${icon("pulse")}${esc(d.status_message)}</span>` : "";
    const temps = d ? Object.values(d.temperatures || {}) : [];
    const tmax = temps.length ? Math.max(...temps) : null;
    return `<header>
      <div class="top">
        ${this._narrow && !this._isCard ? `<button class="icon-btn" data-a="menu">${icon("menu")}</button>` : ""}
        ${units}${conn}<span class="spacer"></span>${health}
        ${tmax != null ? `<span class="hdr-temp ${tmax >= 55 ? "warn" : ""}" title="Hottest internal sensor">${icon("thermo")}${tmax}°C</span>` : ""}
        ${d ? `<button class="icon-btn" title="Refresh details now" data-a="refresh">${icon("refresh")}</button>` : ""}
      </div>
      <nav>${TABS.map(([k, label, ic]) => `<button class="tab ${this._tab === k ? "active" : ""}" data-a="tab" data-tab="${k}">${icon(ic)}<span>${label}</span></button>`).join("")}</nav>
    </header>`;
  }

  /* ---------- layers: video routing, or independent audio routing (sink mode) ---------- */
  get _audioLayer() { return this._layer === "audio"; }
  _audioAllowed() { const m = (this._data && this._data.modes) || {}; return !!m.sink; }
  _audioEditable() { const m = (this._data && this._data.modes) || {}; return !!(m.sink && m.independent_audio); }
  _zones() {
    if (!this._data) return [];
    return this._data.outputs.filter((o) => this._showHidden || !o.hidden)
      .map((o) => (this._audioLayer ? { ...o, source: o.audio_source, video_source: o.source } : o));
  }
  _out(z) { const o = this._data.outputs[z - 1]; return o && this._audioLayer ? { ...o, source: o.audio_source } : o; }
  _visibleInputs() {
    const d = this._data;
    const audio = this._audioLayer;
    const fedAudio = {};
    if (audio) d.outputs.forEach((o) => { if (o.audio_source) (fedAudio[o.audio_source] = fedAudio[o.audio_source] || []).push(o.zone); });
    return d.inputs
      .filter((i) => (audio ? true : i.kind !== "audio"))
      .map((i) => (audio ? { ...i, zones: fedAudio[i.source] || [] } : i))
      .filter((i) => {
        if (i.hidden && !this._showHidden && !i.zones.length) return false;
        switch (this._filter) {
          case "used": return i.zones.length > 0;
          case "signal": return i.signal === "signal";
          default: return true;
        }
      });
  }

  _presetChips() {
    const p = this._data.presets;
    if (!p.length || this._audioLayer) return "";
    return `<div class="chips presets-row">${p.map((x) => `<button class="chip preset" data-a="apply-preset" data-id="${x.id}">${icon("play")}${esc(x.name)}</button>`).join("")}</div>`;
  }

  _selectionBar() {
    const n = this._sel.size;
    if (!n) return `<div class="hint">${icon("info")} ${this._audioLayer
      ? "Audio layer: drag outputs onto an audio source (or onto Disconnect) to set the audio independently of the picture."
      : "Drag outputs (or a group header) onto an input · tap an input to pick the outputs it should go to · drag an input onto another to move all its outputs · long-press to drag on touch screens."}</div>`;
    return `<div class="selbar">
      <span class="count">${n} selected</span>
      <button class="icon-btn tiny" title="Clear selection" data-a="sel-clear">${icon("close")}</button>
      <button class="btn small" data-a="sel-power" data-on="1">${icon("power")}TV on</button>
      <button class="btn small" data-a="sel-power" data-on="0">${icon("power")}Standby</button>
      <button class="btn small" data-a="sel-key" data-code="66" title="CEC volume down">${icon("voldown")}</button>
      <button class="btn small" data-a="sel-key" data-code="65" title="CEC volume up">${icon("volume")}</button>
      <button class="btn small" data-a="sel-key" data-code="67" title="CEC mute">${icon("mute")}</button>
      <span class="muted small">Tap an input to switch ${n > 1 ? "them" : "it"}</span>
    </div>`;
  }

  _tab_routing() {
    const d = this._data;
    const audio = this._audioLayer;
    const inputs = this._visibleInputs();
    const outs = this._filteredOutputs();
    const groups = this._groupsView(outs);
    const filters = [["visible", "All"], ["used", "In use"], ["signal", "With signal"]];
    const ofilters = [["all", "All"], ["on", "TV on"], ["off", "TV off"], ["nosignal", "No signal"], ["poor", "Link issues"]];
    const anyCollapsed = groups && groups.some((g) => this._collapsed.has(g.id));
    const outputsHtml = groups
      ? groups.map((g) => this._groupHead(g) + (this._isCollapsed(g.id) ? "" : `<div class="grp-body">${g.zones.map((o) => this._outputCard(o)).join("")}</div>`)).join("")
      : outs.map((o) => this._outputCard(o)).join("");
    const layerSeg = this._audioAllowed() ? `<div class="seg" title="Routing layer"><button class="${audio ? "" : "active"}" data-a="layer" data-v="video">${icon("video")}Video</button><button class="${audio ? "active" : ""}" data-a="layer" data-v="audio">${icon("volume")}Audio</button></div>` : "";
    const locked = audio && !this._audioEditable();
    return `
      <div class="toolbar">
        ${layerSeg}
        <div class="seg">${filters.map(([k, l]) => `<button class="${this._filter === k ? "active" : ""}" data-a="filter" data-f="${k}">${l}</button>`).join("")}</div>
        <label class="check"><input type="checkbox" data-c="show-hidden" ${this._showHidden ? "checked" : ""}> Show hidden</label>
        <span class="spacer"></span>
        <div class="seg" title="Card density"><button class="${this._compact ? "" : "active"}" data-a="density" data-v="0">Comfortable</button><button class="${this._compact ? "active" : ""}" data-a="density" data-v="1">Compact</button></div>
        <button class="btn small" data-a="select-all">${icon("select")}Select all</button>
      </div>
      ${locked ? `<div class="banner warn">${icon("info")} Independent audio routing is off on the matrix, so each output's audio follows its video. Turn it on in the matrix web UI (Audio Control, Sink mode) to route audio separately.</div>` : ""}
      ${this._presetChips()}
      ${this._selectionBar()}
      <div class="matrix ${this._compact ? "compact" : ""} ${locked ? "locked" : ""}">
        <svg class="lines"></svg>
        <div class="col inputs">
          <div class="col-head">${audio ? "Audio sources" : "Inputs"} <span class="muted">(${inputs.length})</span></div>
          ${audio && !locked ? `<div class="in-card disconnect" data-drop="0">${icon("unlink")}<div class="nm">Disconnect audio</div></div>` : ""}
          ${inputs.map((i) => this._inputCard(i)).join("") || `<div class="muted pad">No inputs match this filter.</div>`}
        </div>
        <div class="gutter"></div>
        <div class="col outputs">
          <div class="col-head">Outputs <span class="muted">(${outs.length}${outs.length !== this._zones().length ? ` of ${this._zones().length}` : ""})</span>
            ${groups ? `<button class="link" data-a="${anyCollapsed ? "expand-all" : "collapse-all"}">${anyCollapsed ? "Expand all" : "Collapse all"}</button>` : ""}</div>
          <div class="out-tools">
            <div class="seg">${ofilters.map(([k, l]) => `<button class="${(this._outFilter || "all") === k ? "active" : ""}" data-a="ofilter" data-f="${k}">${l}</button>`).join("")}</div>
            <input type="search" class="search" placeholder="Find output…" value="${esc(this._search || "")}" data-c="search">
          </div>
          ${outputsHtml || `<div class="muted pad">No outputs match.</div>`}
        </div>
      </div>`;
  }

  _filteredOutputs() {
    const q = (this._search || "").trim().toLowerCase();
    return this._zones().filter((o) => {
      const f = this._outFilter || "all";
      if (f === "on" && o.power !== true) return false;
      if (f === "off" && o.power !== false) return false;
      if (f === "nosignal" && o.signal !== false) return false;
      if (f === "poor" && !(o.link && (o.link.linked === false || (o.link.quality && o.link.quality.rating === "poor")))) return false;
      if (q) {
        const src = o.source ? (this._input(o.source) || {}).name || "" : "";
        if (!(o.name.toLowerCase().includes(q) || src.toLowerCase().includes(q) || `${o.zone}` === q)) return false;
      }
      return true;
    });
  }

  _linkBadge(o) {
    if (!o.link) return `<span class="badge">HDMI</span>`;
    if (o.link.linked === false) return `<span class="badge err" title="No HDBaseT link">No link</span>`;
    const r = o.link.quality && o.link.quality.rating;
    if (r === "poor") return `<span class="badge err" title="HDBaseT link quality">Poor link</span>`;
    if (r === "good") return `<span class="badge ok" title="HDBaseT link quality">${icon("ethernet")}Good</span>`;
    return `<span class="badge">HDBT</span>`;
  }

  _tvState(o) {
    return { on: ["On", "ok"], turning_on: ["Turning on", "ok"], standby: ["Standby", ""], turning_off: ["Going to standby", ""] }[o.tv_power] || ["TV ?", ""];
  }

  _inputCard(i) {
    const color = this._colorFor(i.source);
    const sig = i.signal && SIGNAL[i.signal] ? `<span class="badge ${SIGNAL[i.signal][1]}">${SIGNAL[i.signal][0]}</span>` : "";
    const zones = i.zones.map((z) => this._data.outputs[z - 1]).filter(Boolean);
    const max = this._compact ? 4 : 8;
    const chips = zones.slice(0, max).map((o) => `<span class="mini">${esc(o.name)}</span>`).join("") + (zones.length > max ? `<span class="mini more">+${zones.length - max}</span>` : "");
    const canClear = this._audioLayer && this._audioEditable() && zones.length;
    return `<div class="in-card ${zones.length ? "active draggable" : ""} ${i.hidden ? "is-hidden" : ""}" data-drop="${i.source}" data-src="${i.source}" style="--c:${color}">
      <div class="row"><span class="dot"></span><span class="nm">${esc(i.name)}</span><span class="kind">${i.kind === "audio" ? "A" : ""}${i.index}</span>${sig}
        <span class="spacer"></span>${zones.length ? `<span class="count" title="${zones.length} output(s)">${zones.length}</span>` : ""}
        ${canClear ? `<button class="icon-btn tiny clear-in" title="Disconnect audio from ${zones.length} output(s)" data-a="input-clear" data-src="${i.source}">${icon("unlink")}</button>` : ""}</div>
      ${zones.length ? `<div class="mini-chips">${chips}</div>` : this._compact ? "" : `<div class="muted small">${i.video && i.signal === "signal" ? esc(i.video) : "Not routed"}</div>`}
    </div>`;
  }

  _outputCard(o) {
    const src = o.source ? this._input(o.source) : null;
    const color = this._colorFor(o.source);
    const sel = this._sel.has(o.zone);
    const [tvTxt, tvCls] = this._tvState(o);
    const ctl = `<span class="ctl">
        <button class="icon-btn tiny tv ${o.power ? "on" : o.power === false ? "off" : ""}" title="Display ${o.power ? "to standby" : "on"} (CEC) · ${tvTxt}" data-a="zone-power" data-zone="${o.zone}" data-on="${o.power ? 0 : 1}">${icon("tv")}</button></span>`;
    const cls = `out-card ${sel ? "selected" : ""} ${o.power === false ? "off" : ""} ${o.hidden ? "is-hidden" : ""}`;
    const srcHtml = `<span class="src ${src ? "" : "none"}">${src ? `<span class="dot"></span>${esc(src.name)}` : "No source"}</span>`;
    const warn = o.signal === false && o.power !== false ? `<span class="badge warn" title="No video signal at the display">No signal</span>` : "";
    const audioNote = !this._audioLayer && o.audio_source && o.audio_source !== o.source ? `<span class="badge" title="Audio routed separately">${icon("volume")}${esc((this._input(o.audio_source) || {}).name || "")}</span>` : "";
    if (this._compact) {
      return `<div class="${cls} compact" data-zone="${o.zone}" style="--c:${color}" title="Output ${o.zone}${src ? ` · ${esc(src.name)}` : ""} · ${tvTxt}">
        <div class="row"><span class="sel-box">${sel ? icon("check") : ""}</span><span class="nm">${esc(o.name)}</span>
          <span class="spacer"></span>${this._narrow ? (src ? `<span class="dot"></span>` : "") : `${warn}${srcHtml}`}${o.link && (o.link.linked === false || (o.link.quality || {}).rating === "poor") ? `<span class="dot err-dot" title="HDBaseT link problem"></span>` : ""}${ctl}</div>
      </div>`;
    }
    return `<div class="${cls}" data-zone="${o.zone}" style="--c:${color}" title="Output ${o.zone}">
      <div class="row">
        <span class="sel-box">${sel ? icon("check") : ""}</span>
        <span class="nm">${esc(o.name)}</span>${this._narrow ? "" : `<span class="zn">${o.kind === "hdbt" ? "HDBT" : "HDMI"} ${o.zone}</span>`}
        <span class="spacer"></span>${this._narrow ? "" : this._linkBadge(o)}${ctl}
      </div>
      <div class="row sub">${srcHtml}<span class="spacer"></span>${warn}${audioNote}<span class="tvtxt ${tvCls}">${tvTxt}</span></div>
    </div>`;
  }

  /* ---------- Outputs tab: status overview, pick the input for each output ---------- */
  _tab_outputs() {
    const outs = this._filteredOutputs();
    const inputs = this._data.inputs.filter((i) => i.kind !== "audio" && (!i.hidden || i.zones.length));
    const groups = this._groupsView(outs);
    const ofilters = [["all", "All"], ["on", "TV on"], ["off", "TV off"], ["nosignal", "No signal"], ["poor", "Link issues"]];
    const card = (o) => {
      const [tvTxt, tvCls] = this._tvState(o);
      const src = this._input(o.source);
      return `<div class="zone-card ${o.power === false ? "off" : ""} ${this._sel.has(o.zone) ? "selected" : ""}" style="--c:${this._colorFor(o.source)}">
        <div class="row"><button class="sel-box btnlike" data-a="toggle-sel" data-zone="${o.zone}">${this._sel.has(o.zone) ? icon("check") : ""}</button>
          <span class="nm">${esc(o.name)}</span><span class="zn">${o.kind === "hdbt" ? "HDBT" : "HDMI"} ${o.zone}</span><span class="spacer"></span>${this._linkBadge(o)}</div>
        <label class="lbl-sel">Input<select data-c="zone-source" data-zone="${o.zone}">
          ${o.source ? "" : `<option value="0" selected>— none —</option>`}
          ${inputs.map((i) => `<option value="${i.source}" ${o.source === i.source ? "selected" : ""}>${esc(i.name)}${i.signal === "no_signal" ? " (no signal)" : ""}</option>`).join("")}
        </select></label>
        <div class="facts">
          <div><span class="muted">Display</span><b class="${tvCls}">${tvTxt}</b>${o.monitor ? `<span class="muted small">${esc(o.monitor)}</span>` : ""}</div>
          <div><span class="muted">Picture</span><b>${o.signal === false ? `<span class="warn-txt">No signal</span>` : esc(o.video || (o.signal ? "Signal" : "–"))}</b></div>
          ${o.audio_source && o.audio_source !== o.source ? `<div><span class="muted">Audio</span><b>${esc((this._input(o.audio_source) || {}).name || "")}</b></div>` : ""}
          ${o.link ? `<div><span class="muted">HDBaseT</span><b>${o.link.linked === false ? `<span class="warn-txt">No link</span>` : `${o.link.cable_m != null ? `${o.link.cable_m} m` : "Linked"}`}</b></div>` : ""}
        </div>
        <div class="row acts">
          <button class="btn small ${o.power ? "" : "primary"}" data-a="zone-power" data-zone="${o.zone}" data-on="1">${icon("power")}On</button>
          <button class="btn small" data-a="zone-power" data-zone="${o.zone}" data-on="0">Standby</button>
          <span class="spacer"></span>
          <button class="icon-btn tiny" title="CEC volume down" data-a="zone-key" data-zone="${o.zone}" data-code="66">${icon("voldown")}</button>
          <button class="icon-btn tiny" title="CEC volume up" data-a="zone-key" data-zone="${o.zone}" data-code="65">${icon("volume")}</button>
          <button class="icon-btn tiny" title="CEC mute" data-a="zone-key" data-zone="${o.zone}" data-code="67">${icon("mute")}</button>
        </div>
        ${src ? "" : ""}
      </div>`;
    };
    const body = groups
      ? groups.map((g) => `<div class="zone-grp">${this._groupHead(g, "zones")}${this._isCollapsed(g.id) ? "" : `<div class="grid zones">${g.zones.map(card).join("")}</div>`}</div>`).join("")
      : `<div class="grid zones">${outs.map(card).join("")}</div>`;
    const on = this._data.outputs.filter((o) => o.power).length;
    const nosig = this._data.outputs.filter((o) => o.signal === false && o.power).length;
    const bad = this._data.outputs.filter((o) => o.link && (o.link.linked === false || (o.link.quality || {}).rating === "poor")).length;
    return `<div class="summary-row">
        <div class="stat"><b>${on}</b><span>displays on</span></div>
        <div class="stat"><b>${this._data.outputs.length - on}</b><span>off / unknown</span></div>
        <div class="stat ${nosig ? "warn" : ""}"><b>${nosig}</b><span>on with no signal</span></div>
        <div class="stat ${bad ? "err" : ""}"><b>${bad}</b><span>HDBaseT issues</span></div>
      </div>
      <div class="toolbar">
        <button class="btn small" data-a="all-power" data-on="1">${icon("power")}All displays on</button>
        <button class="btn small" data-a="all-power" data-on="0">${icon("power")}All to standby</button>
        <span class="spacer"></span>
        <div class="seg">${ofilters.map(([k, l]) => `<button class="${(this._outFilter || "all") === k ? "active" : ""}" data-a="ofilter" data-f="${k}">${l}</button>`).join("")}</div>
        <input type="search" class="search" placeholder="Find output…" value="${esc(this._search || "")}" data-c="search">
        <label class="check"><input type="checkbox" data-c="show-hidden" ${this._showHidden ? "checked" : ""}> Show hidden</label>
      </div>
      ${this._sel.size ? this._selectionBar() : ""}
      ${body}`;
  }

  /* ---------- HDBaseT tab ---------- */
  _mseBar(v) {
    if (v == null) return `<span class="mse none">–</span>`;
    // scale -30 dB (excellent) .. -10 dB (bad); threshold -15 dB
    const pct = Math.max(2, Math.min(100, ((v + 30) / 20) * 100));
    return `<span class="mse ${v >= -15 ? "bad" : v >= -18 ? "meh" : "good"}" title="${v} dB"><span style="width:${pct}%"></span><i></i><em>${v.toFixed(1)}</em></span>`;
  }

  _kv(obj) {
    const e = Object.entries(obj || {}).filter(([, v]) => v !== "" && v != null);
    return e.length ? e.map(([k, v]) => `<div class="kv"><span>${esc(k.replace(/([a-z])([A-Z])/g, "$1 $2"))}</span><b>${esc(v)}</b></div>`).join("") : `<span class="muted">–</span>`;
  }

  _tab_hdbt() {
    const d = this._data;
    const rows = d.outputs.filter((o) => o.link);
    const now = (d.server_time || Date.now() / 1000) + (Date.now() - (this._recvAt || Date.now())) / 1000;
    return `<div class="toolbar"><span class="muted">HDBaseT transmitters are in the matrix (one per output); receivers are the neo:Ultra units at each display. Quality follows the manual's rule: all four channels below −15 dB and within 3 dB of each other.</span>
        <span class="spacer"></span><span class="muted small">Details read ${ago(d.last_detail, now)}</span>
        <button class="btn small" data-a="refresh">${icon("refresh")}Re-test now</button></div>
      <div class="hdbt-list">${rows.map((o) => {
        const l = o.link, q = l.quality || {}, ch = q.channels || {}, raw = q.raw || {};
        const errs = ["BER", "TotalBER", "ErrorsCRC", "ErrorsVideo"].filter((k) => raw[k] != null).map((k) => `<span class="${raw[k] ? "warn-txt" : ""}">${k.replace("Errors", "")} ${raw[k]}</span>`).join(" · ");
        return `<div class="card hdbt ${l.linked === false ? "down" : q.rating === "poor" ? "poor" : ""}">
          <div class="hdbt-head"><span class="zn">Output ${o.zone}</span><span class="nm">${esc(o.name)}</span><span class="spacer"></span>
            ${o.hdbt_variant ? `<span class="badge">${o.hdbt_variant === "pro" ? "HDBT Pro" : "HDBT Lite"}</span>` : ""}
            ${l.linked === false ? `<span class="badge err">No link</span>` : `<span class="badge ok">${esc(l.status || "Linked")}</span>`}
            ${q.rating ? `<span class="badge ${q.rating === "good" ? "ok" : "err"}">${q.rating === "good" ? "Good" : "Poor"} quality</span>` : ""}</div>
          ${l.linked === false ? `<p class="muted">No receiver detected. Check the Cat cable, that the neo:Ultra receiver is connected, and that its link LED (amber) is lit.</p>` : `
          <div class="hdbt-grid">
            <div><h4>Link · MSE per pair <span class="muted" style="text-transform:none;letter-spacing:0">(shorter bar = better, dashed line = −15 dB limit)</span></h4>
              <div class="mse-rows">${["A", "B", "C", "D"].map((c) => `<div class="mse-row"><span>Ch ${c}</span>${this._mseBar(ch[c])}</div>`).join("")}</div>
              <div class="muted small">${errs || ""}</div></div>
            <div><h4>Cable</h4><div class="kv"><span>Estimated length</span><b>${l.cable_m != null ? `${l.cable_m} m` : "–"}</b></div>
              <div class="kv"><span>Power over HDBaseT</span><b>${l.poe == null ? "–" : l.poe ? "Yes" : "No"}</b></div>
              <div class="kv"><span>Display</span><b>${esc(o.monitor || "–")}</b></div>
              <div class="kv"><span>Picture</span><b>${esc(o.video || "–")}</b></div></div>
            <div><h4>Transmitter (matrix)</h4>${this._kv(l.transmitter)}</div>
            <div><h4>Receiver</h4>${this._kv(l.receiver)}</div>
          </div>`}
        </div>`;
      }).join("") || `<div class="empty">${icon("ethernet", "big")}<p>This matrix reports no HDBaseT outputs.</p></div>`}</div>`;
  }

  /* ---------- System tab ---------- */
  _tab_system() {
    const d = this._data;
    const now = (d.server_time || Date.now() / 1000) + (Date.now() - (this._recvAt || Date.now())) / 1000;
    const yn = (v) => (v == null ? "–" : v ? "On" : "Off");
    const up = d.uptime ? `${Math.floor(d.uptime / 86400)}d ${Math.floor((d.uptime % 86400) / 3600)}h ${Math.floor((d.uptime % 3600) / 60)}m` : "–";
    const temps = Object.entries(d.temperatures || {});
    return `<div class="grid status">
      <div class="card"><h3>${icon("info")}Unit</h3><table>
        <tr><td>Model</td><td>${esc(d.model)} <span class="muted small">${esc(d.model_code)}</span></td></tr>
        <tr><td>Firmware</td><td>${esc(d.firmware || "–")}</td></tr>
        <tr><td>Serial</td><td>${esc(d.serial || "–")}</td></tr>
        <tr><td>MAC</td><td>${esc(d.mac || "–")}</td></tr>
        <tr><td>Hardware revision</td><td>${esc(d.hardware_revision || "–")}</td></tr>
        <tr><td>Uptime</td><td>${up}</td></tr>
        ${d.leds && d.leds.status != null ? `<tr><td>Status LEDs</td><td>${esc(d.leds.status)}</td></tr>` : ""}
        ${d.leds && d.leds.backlight != null ? `<tr><td>Backlight</td><td>${esc(d.leds.backlight)}</td></tr>` : ""}
        ${d.monitoring && d.monitoring.installer_id ? `<tr><td>Pulse-Eight monitoring</td><td>Installer ${esc(d.monitoring.installer_id)}${d.monitoring.last_contact_s != null ? ` <span class="muted small">· last pulse ${Math.round(d.monitoring.last_contact_s / 60)} min ago</span>` : ""}</td></tr>` : ""}</table></div>
      <div class="card"><h3>${icon("pulse")}Health</h3><table>
        <tr><td>System</td><td><span class="pill ${/health|ok/i.test(d.status_message || "") ? "ok" : "err"}">${esc(d.status_message || "–")}</span></td></tr>
        ${Object.entries(d.health || {}).filter(([k]) => /Message$/.test(k) && k !== "StatusMessage").map(([k, v]) => `<tr><td>${esc(k.replace(/Message$/, "").replace(/([a-z])([A-Z])/g, "$1 $2").replace("PSU1", "Power supply"))}</td><td>${esc(v)}</td></tr>`).join("")}
        ${(d.psu || []).map((p) => `<tr><td>${esc(p.name)}</td><td>${p.value != null ? esc(typeof p.value === "number" ? +p.value.toFixed(2) : p.value) : "–"}${p.ok === false ? ` <span class="pill err">Fault</span>` : ""}</td></tr>`).join("")}
        <tr><td>Connection</td><td><span class="pill ${d.connected ? "ok" : "err"}">${d.connected ? "Connected" : "Offline"}</span> <span class="muted small">${esc(d.host)}</span></td></tr>
        <tr><td>Updates</td><td>${d.udp && d.udp.active ? `<span class="pill ok">Live</span> <span class="muted small">UDP pushes · last ${ago(d.udp.last, now)}</span>` : `<span class="muted">Polling</span>`}</td></tr>
        <tr><td>Last poll</td><td>${ago(d.last_update, now)}</td></tr></table></div>
      <div class="card"><h3>${icon("thermo")}Temperatures</h3>
        ${temps.map(([k, v]) => `<div class="temp-row"><span>Sensor ${+k + 1}</span><span class="tbar ${v >= 55 ? "hot" : v >= 45 ? "warm" : ""}"><span style="width:${Math.min(100, (v / 70) * 100)}%"></span></span><b>${v}°C</b></div>`).join("") || `<p class="muted">Not reported.</p>`}
        <p class="muted small">30–40°C is typical. Keep the rack ventilated.</p></div>
      <div class="card"><h3>${icon("lan")}Network</h3><table>${Object.entries(d.network || {}).map(([k, v]) => `<tr><td>${esc(k.replace(/([a-z])([A-Z])/g, "$1 $2"))}</td><td>${esc(typeof v === "boolean" ? (v ? "Yes" : "No") : v)}</td></tr>`).join("") || `<tr><td>Address</td><td>${esc(d.host)}</td></tr>`}</table></div>
      <div class="card"><h3>${icon("tune")}Features & modes</h3><table>
        <tr><td>HDMI-CEC</td><td>${yn(d.features.cec)}</td></tr>
        <tr><td>CEC source switching</td><td>${yn(d.features.cec_switching)}</td></tr>
        <tr><td>CEC power-on on route change</td><td>${yn(d.modes.cec_on_route)}</td></tr>
        <tr><td>Audio sink mode</td><td>${yn(d.modes.sink)}</td></tr>
        <tr><td>Independent audio routing</td><td>${yn(d.modes.independent_audio)}</td></tr></table>
        <p class="muted small">These are matrix settings; change them in the matrix web UI (Routing Control / Audio Control).</p></div>
      <div class="card wide"><h3>${icon("hdmi")}Inputs</h3><table class="list"><tr><th>#</th><th>Name</th><th>Type</th><th>Signal</th><th>Showing on</th></tr>
        ${d.inputs.map((i) => `<tr><td>${i.index}</td><td><span class="dot" style="--c:${this._colorFor(i.source)}"></span>${esc(i.name)}</td><td>${i.kind === "audio" ? "Digital audio" : "HDMI"}</td>
          <td>${i.signal && SIGNAL[i.signal] ? `<span class="badge ${SIGNAL[i.signal][1]}">${SIGNAL[i.signal][0]}</span>` : "–"} <span class="muted small">${esc(i.video && i.signal === "signal" ? i.video : "")}</span></td>
          <td>${i.zones.map((z) => esc(d.outputs[z - 1].name)).join(", ") || `<span class="muted">–</span>`}</td></tr>`).join("")}</table></div>
      ${(d.mirrors || []).length ? `<div class="card wide"><h3>${icon("hdmi")}Mirror outputs</h3><table class="list"><tr><th>#</th><th>Name</th><th>Type</th><th>Showing</th></tr>
        ${d.mirrors.map((m) => `<tr><td>${m.bay}</td><td>${esc(m.name)}</td><td>${esc(m.type || "HDMI")}</td><td>${m.source ? `<span class="dot" style="--c:${this._colorFor(m.source)}"></span>${esc((this._input(m.source) || {}).name || `Input ${m.source}`)}` : `<span class="muted">–</span>`}</td></tr>`).join("")}</table>
        <p class="muted small">Mirror ports copy the matching output's picture and follow its routing.</p></div>` : ""}
      <div class="card wide"><h3>${icon("alert")}Recent errors</h3>${d.errors.length ? `<table class="list">${[...d.errors].reverse().slice(0, 12).map((e) => `<tr><td class="small">${ago(e.time, now)}</td><td>${esc(e.message)}</td></tr>`).join("")}</table>` : `<p class="muted">No errors.</p>`}</div>
    </div>`;
  }

  /* ---------- Presets ---------- */
  _tab_presets() {
    const d = this._data;
    if (this._editor) return this._presetEditor();
    const outName = (z) => (d.outputs[z - 1] || {}).name || `Output ${z}`;
    return `<div class="toolbar"><span class="muted">Presets also appear as buttons in Home Assistant and can be used with the <code>${DOMAIN}.apply_preset</code> action.</span>
        <span class="spacer"></span>${this._isAdmin ? `<button class="btn primary" data-a="new-preset">${icon("plus")}New preset</button>` : ""}</div>
      ${d.presets.length ? `<div class="grid presets">${d.presets.map((p) => {
        const groups = {};
        for (const [z, s] of Object.entries(p.routes)) (groups[s] = groups[s] || []).push(+z);
        return `<div class="preset-card">
          <button class="apply" data-a="apply-preset" data-id="${p.id}">${icon("play", "big")}<span class="nm">${esc(p.name)}</span></button>
          <div class="desc">${Object.entries(groups).map(([s, zs]) => `<div><span class="dot" style="--c:${this._colorFor(+s)}"></span><b>${esc((this._input(+s) || {}).name || `Input ${s}`)}</b> → ${zs.map(outName).map(esc).join(", ")}</div>`).join("")}
            <div class="muted small">${[p.power_on && "turn displays on", p.power_off_others && "others to standby"].filter(Boolean).join(" · ")}</div></div>
          ${this._isAdmin ? `<div class="acts"><button class="icon-btn" data-a="edit-preset" data-id="${p.id}" title="Edit">${icon("edit")}</button><button class="icon-btn" data-a="delete-preset" data-id="${p.id}" title="Delete">${icon("del")}</button></div>` : ""}
        </div>`; }).join("")}</div>`
      : `<div class="empty">${icon("star", "big")}<p>No presets yet. Create one like <i>“Movie night”</i> (Blu-ray → Cinema + Lounge, others to standby) or <i>“Sky everywhere”</i>.</p></div>`}`;
  }

  _presetEditor() {
    const d = this._data, e = this._editor;
    const inputs = d.inputs.filter((i) => i.kind !== "audio" && (!i.hidden || i.zones.length));
    const opts = (val) => `<option value="" ${val == null ? "selected" : ""}>— not in preset —</option>` +
      inputs.map((i) => `<option value="${i.source}" ${val === i.source ? "selected" : ""}>${esc(i.name)}</option>`).join("");
    return `<div class="editor">
      <h2>${e.id ? "Edit preset" : "New preset"}</h2>
      <div class="form">
        <label>Name<input type="text" data-c="ed-name" value="${esc(e.name)}" placeholder="e.g. Movie night"></label>
        <label>Icon<input type="text" data-c="ed-icon" value="${esc(e.icon || "mdi:television-play")}" placeholder="mdi:movie-open"></label>
      </div>
      <div class="ed-tools">
        <label>Input <select data-c="ed-source">${inputs.map((i) => `<option value="${i.source}" ${e.source === i.source ? "selected" : ""}>${esc(i.name)}</option>`).join("")}</select></label>
        <span class="muted">Tick outputs to show this input on.</span>
        <span class="spacer"></span>
        <button class="btn small" data-a="ed-all">Tick all</button>
        <button class="btn small" data-a="ed-none">Untick all</button>
        <button class="btn small" data-a="ed-capture" title="Copy what is routed right now">${icon("capture")}Use current routing</button>
        <label class="check"><input type="checkbox" data-c="ed-advanced" ${e.advanced ? "checked" : ""}> Mixed inputs</label>
      </div>
      ${(d.groups || []).length ? `<div class="chips ed-groups"><span class="muted small">Tick a group:</span>${d.groups.map((g) => {
        const all = g.zones.length && g.zones.every((z) => e.routes[z] != null);
        return `<button class="chip ${all ? "on" : ""}" data-a="ed-group" data-zones="${g.zones.join(",")}">${icon(all ? "check" : "group")}${esc(g.name)} <span class="muted small">${g.zones.length}</span></button>`;
      }).join("")}</div>` : ""}
      <div class="grid ed-zones">${d.outputs.filter((o) => !o.hidden || e.routes[o.zone] != null).map((o) => {
        const v = e.routes[o.zone];
        return e.advanced
          ? `<label class="ed-zone ${v != null ? "on" : ""}"><span>${esc(o.name)} <span class="muted">${o.zone}</span></span><select data-c="ed-zone-src" data-zone="${o.zone}">${opts(v)}</select></label>`
          : `<label class="ed-zone ${v != null ? "on" : ""}" style="--c:${this._colorFor(v)}"><input type="checkbox" data-c="ed-zone" data-zone="${o.zone}" ${v != null ? "checked" : ""}><span>${esc(o.name)} <span class="muted">${o.zone}</span></span>${v != null && v !== e.source ? `<span class="badge">${esc((this._input(v) || {}).name || "")}</span>` : ""}</label>`;
      }).join("")}</div>
      <div class="form opts">
        <label class="check"><input type="checkbox" data-c="ed-power" ${e.power_on ? "checked" : ""}> Turn those displays on (CEC)</label>
        <label class="check"><input type="checkbox" data-c="ed-poweroff" ${e.power_off_others ? "checked" : ""}> Put all other displays in standby (CEC)</label>
      </div>
      <div class="actions"><button class="btn" data-a="ed-cancel">Cancel</button><button class="btn primary" data-a="ed-save">${icon("check")}Save preset</button></div>
    </div>`;
  }

  /* ---------- Settings: names live on the matrix ---------- */
  _ensureDrafts() {
    if (this._drafts) return;
    const d = this._data;
    this._drafts = {
      inputs: Object.fromEntries(d.inputs.map((i) => [i.source, i.name])),
      outputs: Object.fromEntries(d.outputs.map((o) => [o.zone, o.name])),
      hidden_inputs: new Set(d.inputs.filter((i) => i.hidden).map((i) => i.source)),
      hidden_outputs: new Set(d.outputs.filter((o) => o.hidden).map((o) => o.zone)),
      groups: (d.groups || []).map((g) => ({ ...g, zones: [...g.zones] })),
      groupsDirty: false, hiddenDirty: false, dirty: false,
    };
  }
  _draftGroupOf(zone) { return this._drafts.groups.find((g) => g.zones.includes(zone)); }

  _tab_settings() {
    const d = this._data;
    this._ensureDrafts();
    const dr = this._drafts, admin = this._isAdmin, dis = admin ? "" : "disabled";
    const groupOpts = (z) => { const cur = this._draftGroupOf(z); return `<option value="">—</option>` + dr.groups.map((g, n) => `<option value="${n}" ${cur === g ? "selected" : ""}>${esc(g.name || `Group ${n + 1}`)}</option>`).join(""); };
    const changed = (mode, n, v) => (mode === "in" ? d.inputs[n - 1] : d.outputs[n - 1]).name !== v;
    return `<div class="toolbar">
        ${admin ? `<span class="muted">Names are read from the matrix. Edited names are written back to the matrix when you save, so its web UI and other control systems see them too.</span>` : `<span class="banner warn small">Only administrators can change settings.</span>`}
        <span class="spacer"></span>
        ${dr.dirty ? `<span class="muted">Unsaved changes</span>` : ""}
        <button class="btn" data-a="settings-revert" ${dr.dirty ? "" : "disabled"}>Revert</button>
        <button class="btn primary" data-a="settings-save" ${dr.dirty && admin ? "" : "disabled"}>${icon("check")}Save</button>
      </div>
      <div class="settings-cols">
        <div>
        <div class="card groups-card"><h3>${icon("group")}Output groups</h3>
          <p class="muted small">Groups collapse long output lists (e.g. Downstairs, Upstairs, Outside). Drag a group header onto an input to switch the whole group. Also usable in actions: <code>group: Downstairs</code>. Stored in Home Assistant.</p>
          ${dr.groups.map((g, n) => `<div class="grp-row">
            <input type="text" value="${esc(g.name)}" placeholder="Group name" data-c="grp-name" data-group="${n}" ${dis}>
            <span class="muted small nowrap">${g.zones.length} output${g.zones.length === 1 ? "" : "s"}</span>
            <button class="icon-btn tiny" title="Move up" data-a="grp-up" data-group="${n}" ${n && admin ? "" : "disabled"}>${icon("up")}</button>
            <button class="icon-btn tiny" title="Move down" data-a="grp-down" data-group="${n}" ${n < dr.groups.length - 1 && admin ? "" : "disabled"}>${icon("down")}</button>
            <button class="icon-btn tiny" title="Delete group" data-a="grp-del" data-group="${n}" ${dis}>${icon("del")}</button></div>`).join("") || `<p class="muted">No groups yet.</p>`}
          <button class="btn small" data-a="grp-add" ${dis}>${icon("plus")}Add group</button>
        </div>
        <div class="card"><h3>${icon("tv")}Outputs</h3>
          <table class="list names"><tr><th>#</th><th>Name (on matrix)</th>${dr.groups.length ? "<th>Group</th>" : ""}<th title="Shown in the panel">Show</th></tr>
          ${d.outputs.map((o) => `<tr><td>${o.zone}<div class="muted small">${o.kind === "hdbt" ? "HDBT" : "HDMI"}</div></td><td><input type="text" value="${esc(dr.outputs[o.zone])}" data-c="name-out" data-zone="${o.zone}" class="${changed("out", o.zone, dr.outputs[o.zone]) ? "edited" : ""}" ${dis}></td>
            ${dr.groups.length ? `<td class="grp-sel"><select data-c="zone-group" data-zone="${o.zone}" ${dis}>${groupOpts(o.zone)}</select></td>` : ""}
            <td><input type="checkbox" data-c="vis-out" data-zone="${o.zone}" ${dr.hidden_outputs.has(o.zone) ? "" : "checked"} ${dis}></td></tr>`).join("")}</table></div>
        </div>
        <div class="card"><h3>${icon("hdmi")}Inputs</h3>
          ${(() => { const hasEdid = d.inputs.some((i) => i.edid != null); const opts = d.edid_options || [];
            const edidSel = (i) => { if (i.edid == null) return `<span class="muted">–</span>`; const o = opts.some((x) => x.value === i.edid) ? opts : [...opts, { value: i.edid, label: `Custom profile ${i.edid}` }];
              return `<select data-c="edid" data-src="${i.source}" title="Applied immediately" ${dis}>${o.map((x) => `<option value="${x.value}" ${x.value === i.edid ? "selected" : ""}>${esc(x.label)}</option>`).join("")}</select>`; };
            return `<table class="list names"><tr><th>#</th><th>Name (on matrix)</th>${hasEdid ? `<th title="What the matrix tells this source the displays can show">EDID</th>` : ""}<th>Show</th></tr>
          ${d.inputs.map((i) => `<tr><td>${i.index}<div class="muted small">${i.kind === "audio" ? "Audio" : "HDMI"}</div></td><td><input type="text" value="${esc(dr.inputs[i.source])}" data-c="name-in" data-src="${i.source}" class="${changed("in", i.source, dr.inputs[i.source]) ? "edited" : ""}" ${dis}></td>
            ${hasEdid ? `<td class="grp-sel">${i.kind === "audio" ? "" : edidSel(i)}</td>` : ""}
            <td><input type="checkbox" data-c="vis-in" data-src="${i.source}" ${dr.hidden_inputs.has(i.source) ? "" : "checked"} ${dis}></td></tr>`).join("")}</table>
          ${hasEdid ? `<p class="muted small">EDID changes are sent to the matrix straight away. <b>Dynamic</b> lets the matrix pick a format every connected display supports; <b>Copy output N</b> uses that display's own EDID.</p>` : ""}`; })()}
          <p class="muted small">Tip: Alexa needs input and output names that start differently (e.g. “Sky” and “Mini Sky”, not “Sky 1” and “Sky 2”).</p></div>
      </div>`;
  }

  /* ---------- modal: confirm, or "send this input to…" sheet ---------- */
  _modalHtml() {
    if (this._sendTo) {
      const s = this._sendTo, inp = this._input(s.source), d = this._data;
      const outs = d.outputs.filter((o) => this._showHidden || !o.hidden || o.source === s.source);
      return `<div class="modal-bg" data-a="sendto-cancel"><div class="modal wide-modal" data-stop="1">
        <h3><span class="dot" style="--c:${this._colorFor(s.source)}"></span>Send ${esc(inp.name)} to…</h3>
        <p class="muted small">${inp.signal === "no_signal" ? "⚠ This input currently has no signal. " : ""}Outputs already showing ${esc(inp.name)} are marked.</p>
        ${(d.groups || []).length ? `<div class="chips">${d.groups.map((g) => `<button class="chip" data-a="sendto-group" data-zones="${g.zones.join(",")}">${icon("group")}${esc(g.name)}</button>`).join("")}</div>` : ""}
        <div class="grid ed-zones">${outs.map((o) => {
          const already = o.source === s.source, on = s.picked.has(o.zone), blocked = !this._allowed(o.zone, s.source);
          return `<button class="ed-zone pick ${on ? "on" : ""} ${already || blocked ? "already" : ""}" style="--c:${this._colorFor(s.source)}" data-a="sendto-toggle" data-zone="${o.zone}" ${already || blocked ? "disabled" : ""}>
            <span class="sel-box">${on || already ? icon("check") : ""}</span><span>${esc(o.name)}<div class="muted small">${blocked ? "not allowed on this output" : already ? "already showing" : o.source ? `now: ${esc((this._input(o.source) || {}).name || "")}` : "no source"}</div></span></button>`;
        }).join("")}</div>
        <label class="check"><input type="checkbox" data-c="sendto-power" ${s.power ? "checked" : ""}> Turn those displays on (CEC)</label>
        <div class="actions"><button class="btn" data-a="sendto-cancel">Cancel</button>
          <button class="btn primary" data-a="sendto-apply" ${s.picked.size ? "" : "disabled"}>${icon("check")}Switch ${s.picked.size || ""} output${s.picked.size === 1 ? "" : "s"}</button></div>
      </div></div>`;
    }
    if (!this._modal) return "";
    const m = this._modal;
    return `<div class="modal-bg" data-a="modal-cancel"><div class="modal" data-stop="1">
      <h3>${esc(m.title)}</h3><p>${esc(m.text)}</p>
      <div class="actions"><button class="btn" data-a="modal-cancel">Cancel</button><button class="btn ${m.danger ? "danger" : "primary"}" data-a="modal-ok">${esc(m.ok || "OK")}</button></div>
    </div></div>`;
  }

  /** Apply [[zone, source], ...] with Undo. Video layer: route; audio layer: audio_route. */
  /** Whether the matrix allows this input on this output (Port/Details AllowedSources). */
  _allowed(zone, source) {
    const a = (this._data.outputs[zone - 1] || {}).allowed_sources;
    return !a || !source || a.includes(source);
  }

  async _routeWithUndo(pairs, message, extra = {}) {
    const layer = this._audioLayer ? "audio" : "video";
    if (layer === "video") {
      const blocked = pairs.filter(([z, s]) => !this._allowed(z, s));
      if (blocked.length) {
        pairs = pairs.filter(([z, s]) => this._allowed(z, s));
        const names = blocked.map(([z]) => this._data.outputs[z - 1].name).join(", ");
        if (!pairs.length) { this._showToast(`Not allowed by the matrix on ${names}`, true); return; }
        message += ` · skipped ${names} (not allowed)`;
      }
    }
    const field = layer === "audio" ? "audio_source" : "source";
    const prev = pairs.map(([z]) => [z, (this._data.outputs[z - 1] || {})[field] || 0])
      .filter(([z, s]) => s !== pairs.find((p) => p[0] === z)[1] && (layer === "audio" || s > 0));
    const bySource = new Map();
    for (const [z, s] of pairs) bySource.set(s, [...(bySource.get(s) || []), z]);
    for (const [s, zs] of bySource) await this._ws(layer === "audio" ? "audio_route" : "route", { zones: zs, source: s, ...(layer === "video" ? extra : {}) });
    this._showToast(message, false, prev.length ? { pairs: prev, layer } : null);
  }

  async _undo() {
    const t = this._toast;
    if (!t || !t.undo) return;
    this._toast = null; this._renderToast();
    const bySource = new Map();
    for (const [z, s] of t.undo.pairs) bySource.set(s, [...(bySource.get(s) || []), z]);
    for (const [s, zs] of bySource) await this._ws(t.undo.layer === "audio" ? "audio_route" : "route", { zones: zs, source: s });
    this._showToast(`Restored ${t.undo.pairs.length} output${t.undo.pairs.length > 1 ? "s" : ""}`);
  }

  async _clearInput(source) {
    if (!this._audioLayer) return;
    const inp = this._visibleInputs().find((i) => i.source === source);
    if (!inp || !inp.zones.length) return;
    await this._routeWithUndo(inp.zones.map((z) => [z, 0]), `Disconnected audio from ${inp.zones.length} output${inp.zones.length > 1 ? "s" : ""}`);
  }

  async _moveInput(from, to) {
    const a = this._visibleInputs().find((i) => i.source === from), b = this._input(to);
    if (!a || !a.zones.length || from === to) return;
    if (!this._audioLayer && b && b.kind === "audio") return;
    await this._routeWithUndo(a.zones.map((z) => [z, to]), `Moved ${a.zones.length} output${a.zones.length > 1 ? "s" : ""} from ${a.name} → ${b ? b.name : "input"}`);
  }

  async _onClick(ev) {
    if (this._suppressClick) { this._suppressClick = false; return; }
    const t = ev.target.closest("[data-a]");
    const card = ev.target.closest(".out-card");
    if (!t && card) { this._toggleSel(+card.dataset.zone); return; }
    const head = !t && ev.target.closest(".grp-head");
    if (head) { this._toggleCollapsed(head.dataset.group); return; }
    if (!t) {
      const inCard = ev.target.closest(".in-card");
      if (!inCard || inCard.closest(".matrix.locked")) return;
      const src = +inCard.dataset.drop;
      if (this._sel.size) await this._routeSel(src);
      else if (!this._audioLayer && src) { this._sendTo = { source: src, picked: new Set(), power: true }; this._render(); }
      return;
    }
    if (t.classList.contains("modal-bg") && ev.target.closest("[data-stop]")) return;
    const a = t.dataset.a;
    const zones = [...this._sel];
    const nums = (s) => s.split(",").filter(Boolean).map(Number);
    switch (a) {
      case "undo": await this._undo(); break;
      case "layer": this._layer = t.dataset.v; this._sel.clear(); this._render(); break;
      case "density": this._setPref("compact", t.dataset.v === "1"); this._render(); break;
      case "ofilter": this._outFilter = t.dataset.f; this._render(); break;
      case "toggle-group": this._toggleCollapsed(t.dataset.group); break;
      case "collapse-all": (this._data.groups || []).forEach((g) => this._collapsed.add(g.id)); this._collapsed.add("_other"); this._setPref("collapsed", [...this._collapsed]); this._render(); break;
      case "expand-all": this._collapsed.clear(); this._setPref("collapsed", []); this._render(); break;
      case "sel-group": {
        const zs = nums(t.dataset.zones), all = zs.every((z) => this._sel.has(z));
        zs.forEach((z) => (all ? this._sel.delete(z) : this._sel.add(z)));
        this._render(); break;
      }
      case "grp-power": await this._ws("cec_power", { zones: nums(t.dataset.zones), on: t.dataset.on === "1" }, t.dataset.on === "1" ? "Displays on" : "Displays to standby"); break;
      case "input-clear": ev.stopPropagation(); await this._clearInput(+t.dataset.src); break;
      case "grp-add": this._drafts.groups.push({ name: `Group ${this._drafts.groups.length + 1}`, zones: [] }); this._drafts.groupsDirty = this._drafts.dirty = true; this._render(); break;
      case "grp-del": this._drafts.groups.splice(+t.dataset.group, 1); this._drafts.groupsDirty = this._drafts.dirty = true; this._render(); break;
      case "grp-up": case "grp-down": {
        const g = this._drafts.groups, i = +t.dataset.group, j = a === "grp-up" ? i - 1 : i + 1;
        [g[i], g[j]] = [g[j], g[i]]; this._drafts.groupsDirty = this._drafts.dirty = true; this._render(); break;
      }
      case "ed-group": {
        const e = this._editor, zs = nums(t.dataset.zones), all = zs.every((z) => e.routes[z] != null);
        zs.forEach((z) => { if (all) delete e.routes[z]; else e.routes[z] = e.source; });
        this._render(); break;
      }
      case "menu": this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true })); break;
      case "tab": this._tab = t.dataset.tab; if (this._tab !== "settings") this._drafts = null; if (this._tab !== "routing") this._layer = "video"; this._render(); break;
      case "filter": this._filter = t.dataset.f; this._render(); break;
      case "zone-power": ev.stopPropagation(); await this._ws("cec_power", { zones: [+t.dataset.zone], on: t.dataset.on === "1" }); break;
      case "zone-key": await this._ws("cec_key", { zones: [+t.dataset.zone], code: +t.dataset.code }); break;
      case "toggle-sel": this._toggleSel(+t.dataset.zone); break;
      case "select-all": this._zones().forEach((o) => this._sel.add(o.zone)); this._render(); break;
      case "sel-clear": this._sel.clear(); this._render(); break;
      case "sel-power": await this._ws("cec_power", { zones, on: t.dataset.on === "1" }, `${zones.length} display${zones.length > 1 ? "s" : ""} ${t.dataset.on === "1" ? "on" : "to standby"}`); break;
      case "sel-key": await this._ws("cec_key", { zones, code: +t.dataset.code }); break;
      case "all-power": {
        const on = t.dataset.on === "1", zs = this._zones().map((o) => o.zone);
        if (!on) this._confirm("Put all displays in standby?", `Sends CEC standby to ${zs.length} displays.`, "Standby all", true, () => this._ws("cec_power", { zones: zs, on: false }, "All displays to standby"));
        else await this._ws("cec_power", { zones: zs, on: true }, "All displays on");
        break;
      }
      case "sendto-toggle": { const z = +t.dataset.zone, p = this._sendTo.picked; p.has(z) ? p.delete(z) : p.add(z); this._render(); break; }
      case "sendto-group": { const p = this._sendTo.picked, zs = nums(t.dataset.zones).filter((z) => this._data.outputs[z - 1].source !== this._sendTo.source && this._allowed(z, this._sendTo.source)); const all = zs.every((z) => p.has(z)); zs.forEach((z) => (all ? p.delete(z) : p.add(z))); this._render(); break; }
      case "sendto-cancel": if (ev.target === t || t.tagName === "BUTTON") { this._sendTo = null; this._render(); } break;
      case "sendto-apply": {
        const s = this._sendTo; this._sendTo = null; this._render();
        const inp = this._input(s.source);
        await this._routeWithUndo([...s.picked].map((z) => [z, s.source]), `${inp.name} → ${s.picked.size} output${s.picked.size > 1 ? "s" : ""}`, { power_on: s.power });
        break;
      }
      case "apply-preset": { const p = this._data.presets.find((x) => x.id === t.dataset.id); await this._ws("apply_preset", { preset: t.dataset.id }, `Applied “${p ? p.name : "preset"}”`); break; }
      case "new-preset": this._editor = { name: "", icon: "mdi:television-play", routes: {}, source: (this._data.inputs.find((i) => !i.hidden && i.kind !== "audio") || this._data.inputs[0]).source, power_on: true, power_off_others: false, advanced: false }; this._render(); break;
      case "edit-preset": {
        const p = this._data.presets.find((x) => x.id === t.dataset.id);
        const routes = Object.fromEntries(Object.entries(p.routes).map(([z, s]) => [+z, +s]));
        const sources = [...new Set(Object.values(routes))];
        this._editor = { ...p, routes, source: sources[0] ?? this._data.inputs[0].source, advanced: sources.length > 1 };
        this._render(); break;
      }
      case "delete-preset": { const p = this._data.presets.find((x) => x.id === t.dataset.id); this._confirm(`Delete “${p.name}”?`, "The preset and its Home Assistant button will be removed.", "Delete", true, () => this._ws("delete_preset", { preset_id: p.id }, "Preset deleted")); break; }
      case "ed-all": this._data.outputs.forEach((o) => { if (!o.hidden) this._editor.routes[o.zone] = this._editor.source; }); this._render(); break;
      case "ed-none": this._editor.routes = {}; this._render(); break;
      case "ed-capture": {
        const r = {}; this._data.outputs.forEach((o) => { if (o.source) r[o.zone] = o.source; });
        this._editor.routes = r; this._editor.advanced = new Set(Object.values(r)).size > 1; this._render(); break;
      }
      case "ed-cancel": this._editor = null; this._render(); break;
      case "ed-save": {
        const e = this._editor;
        if (!e.name.trim()) { this._showToast("Give the preset a name", true); break; }
        if (!Object.keys(e.routes).length) { this._showToast("Tick at least one output", true); break; }
        await this._ws("save_preset", { preset: { id: e.id, name: e.name, icon: e.icon, routes: e.routes, power_on: e.power_on, power_off_others: e.power_off_others } }, "Preset saved");
        this._editor = null; this._render(); break;
      }
      case "refresh": await this._ws("refresh", {}, "Details refreshed"); break;
      case "settings-revert": this._drafts = null; this._render(); break;
      case "settings-save": {
        const dr = this._drafts, d = this._data;
        let renamed = 0;
        for (const i of d.inputs) { const v = (dr.inputs[i.source] || "").trim(); if (v && v !== i.name) { await this._ws("rename", { mode: "Input", number: i.source, name: v }); renamed++; } }
        for (const o of d.outputs) { const v = (dr.outputs[o.zone] || "").trim(); if (v && v !== o.name) { await this._ws("rename", { mode: "Output", number: o.zone, name: v }); renamed++; } }
        if (dr.hiddenDirty) await this._ws("set_hidden", { hidden_inputs: [...dr.hidden_inputs], hidden_outputs: [...dr.hidden_outputs] });
        if (dr.groupsDirty) await this._ws("save_groups", { groups: dr.groups.map((g) => ({ id: g.id, name: g.name || "Group", zones: g.zones })) });
        this._showToast(renamed ? `Saved · ${renamed} name${renamed > 1 ? "s" : ""} written to the matrix` : "Settings saved");
        this._drafts = null; this._interacting = false; this._render(); break;
      }
      case "modal-cancel": if (ev.target === t || t.tagName === "BUTTON") { this._modal = null; this._render(); } break;
      case "modal-ok": { const fn = this._modal.fn; this._modal = null; this._render(); await fn(); break; }
    }
  }

  async _onChange(ev) {
    const t = ev.target, c = t.dataset.c;
    this._sliding = false;
    switch (c) {
      case "unit": this._entry = t.value; this._sel.clear(); this._drafts = null; this._editor = null; this._subscribe(); break;
      case "show-hidden": this._showHidden = t.checked; this._render(); break;
      case "zone-source": {
        const z = +t.dataset.zone, s = +t.value, o = this._data.outputs[z - 1];
        if (s) await this._routeWithUndo([[z, s]], `${o.name} → ${(this._input(s) || {}).name}`);
        break;
      }
      case "sendto-power": this._sendTo.power = t.checked; break;
      case "edid": { const i = this._input(+t.dataset.src); await this._ws("set_edid", { number: +t.dataset.src, profile: +t.value }, `${i ? i.name : "Input"}: EDID updated`); break; }
      case "ed-source": {
        const s = +t.value, e = this._editor;
        for (const z of Object.keys(e.routes)) e.routes[z] = s;
        e.source = s; this._render(); break;
      }
      case "ed-zone": { const e = this._editor; if (t.checked) e.routes[+t.dataset.zone] = e.source; else delete e.routes[+t.dataset.zone]; this._render(); break; }
      case "ed-zone-src": { const e = this._editor; if (t.value === "") delete e.routes[+t.dataset.zone]; else e.routes[+t.dataset.zone] = +t.value; this._render(); break; }
      case "ed-advanced": this._editor.advanced = t.checked; this._render(); break;
      case "ed-power": this._editor.power_on = t.checked; break;
      case "ed-poweroff": this._editor.power_off_others = t.checked; break;
      case "zone-group": {
        const z = +t.dataset.zone;
        this._drafts.groups.forEach((g) => { g.zones = g.zones.filter((x) => x !== z); });
        if (t.value !== "") { const g = this._drafts.groups[+t.value]; g.zones = [...g.zones, z].sort((a, b) => a - b); }
        this._drafts.groupsDirty = this._drafts.dirty = true; this._render(); break;
      }
      case "vis-in": this._drafts.hidden_inputs[t.checked ? "delete" : "add"](+t.dataset.src); this._drafts.hiddenDirty = true; this._markDirty(); break;
      case "vis-out": this._drafts.hidden_outputs[t.checked ? "delete" : "add"](+t.dataset.zone); this._drafts.hiddenDirty = true; this._markDirty(); break;
    }
  }

  _toggleSel(z) { this._sel.has(z) ? this._sel.delete(z) : this._sel.add(z); this._render(); }

  async _routeSel(source, zones) {
    zones = zones || [...this._sel];
    if (!zones.length) return;
    const name = source ? (this._input(source) || {}).name : "Disconnected";
    await this._routeWithUndo(zones.map((z) => [z, source]), `${zones.length} output${zones.length > 1 ? "s" : ""} → ${name}`);
    this._sel.clear();
    this._render();
  }

  /** Apply [[zone, source], ...] and offer Undo (restores the previous routing). */




  _onInput(ev) {
    const t = ev.target, c = t.dataset.c;
    if (c === "master") { const v = this.shadowRoot.getElementById("master-val"); if (v) v.textContent = dbLabel(+t.value); }
    else if (c === "zone-volume") { const v = this.shadowRoot.querySelector(`[data-volval="${t.dataset.zone}"]`); if (v) v.textContent = `${t.value}%`; }
    else if (c === "sel-volume") { const v = this.shadowRoot.getElementById("selvol"); if (v) v.textContent = `${t.value}%`; }
    else if (c === "ed-volume") { this._editor.volume = +t.value; const v = this.shadowRoot.getElementById("edvol"); if (v) v.textContent = `${t.value}%`; }
    else if (c === "ed-name") this._editor.name = t.value;
    else if (c === "ed-icon") this._editor.icon = t.value;
    else if (c === "search") { this._search = t.value; this._render(); }
    else if (c === "name-in") { this._drafts.inputs[t.dataset.src] = t.value; this._markDirty(); }
    else if (c === "name-out") { this._drafts.outputs[t.dataset.zone] = t.value; this._markDirty(); }
    else if (c === "grp-name") { this._drafts.groups[+t.dataset.group].name = t.value; this._drafts.groupsDirty = true; this._markDirty(); }
  }

  _markDirty() {
    if (this._drafts.dirty) return;
    this._drafts.dirty = true;
    const save = this.shadowRoot.querySelector('[data-a="settings-save"]'), rev = this.shadowRoot.querySelector('[data-a="settings-revert"]');
    if (save && this._isAdmin) save.disabled = false;
    if (rev) rev.disabled = false;
  }

  _onPointerDown(ev) {
    if (ev.target.closest("input[type=range]")) { this._sliding = true; const up = () => { this._sliding = false; window.removeEventListener("pointerup", up); this._scheduleRender(); }; window.addEventListener("pointerup", up); return; }
    if (ev.target.closest("[data-a]") || ev.target.closest("input, select") || ev.button > 0 || ev.target.closest(".matrix.locked")) return;
    const card = ev.target.closest(".out-card");
    const head = !card && ev.target.closest(".matrix .grp-head");
    const inCard = !card && !head && ev.target.closest(".in-card.draggable");
    if (!card && !head && !inCard) return;
    const start = { x: ev.clientX, y: ev.clientY };
    const touch = ev.pointerType === "touch";
    let dragging = false, longTimer = null;

    const payload = () => {
      if (card) { const z = +card.dataset.zone; return { zones: this._sel.has(z) ? [...this._sel] : [z] }; }
      if (head) return { zones: head.dataset.zones.split(",").map(Number), group: head.querySelector(".nm").textContent };
      return { input: +inCard.dataset.src };
    };
    const begin = () => {
      dragging = true;
      const p = payload();
      let label;
      if (p.input) { const i = this._visibleInputs().find((x) => x.source === p.input) || this._input(p.input); label = `${i.name} · ${i.zones.length} zone${i.zones.length > 1 ? "s" : ""}`; }
      else if (p.group) label = `${p.group} · ${p.zones.length} zone${p.zones.length > 1 ? "s" : ""}`;
      else { const names = p.zones.map((z) => this._out(z).name); label = `${names[0]}${names.length > 1 ? ` +${names.length - 1}` : ""}`; }
      const ghost = document.createElement("div");
      ghost.className = `drag-ghost ${p.input ? "input" : ""}`;
      if (p.input) ghost.style.setProperty("--c", this._colorFor(p.input));
      ghost.innerHTML = `${icon(p.input ? "input" : p.group ? "group" : "speaker")}<span>${esc(label)}</span>`;
      const app = this.shadowRoot.querySelector(".app");
      app.appendChild(ghost);
      app.classList.add("dragging");
      if (p.input) app.classList.add("dragging-input");
      this._drag = { ...p, ghost, over: null };
      (p.zones || []).forEach((z) => { const el = this.shadowRoot.querySelector(`.out-card[data-zone="${z}"]`); if (el) el.classList.add("lifted"); });
      if (p.input) inCard.classList.add("lifted");
      if (head) head.classList.add("lifted");
      if (navigator.vibrate && touch) navigator.vibrate(15);
    };
    const move = (e) => {
      if (!dragging) {
        const dist = Math.hypot(e.clientX - start.x, e.clientY - start.y);
        if (touch) { if (dist > 10) cleanup(); return; }
        if (dist < 6) return;
        begin();
      }
      e.preventDefault();
      const d = this._drag;
      d.ghost.style.transform = `translate(${e.clientX + 12}px, ${e.clientY + 12}px)`;
      const el = this.shadowRoot.elementFromPoint(e.clientX, e.clientY);
      let target = el && el.closest(".in-card");
      if (target && d.input && +target.dataset.drop === d.input) target = null; // not onto itself
      if (d.over !== target) { if (d.over) d.over.classList.remove("drop-over"); if (target) target.classList.add("drop-over"); d.over = target; }
      this._autoScroll(e.clientY);
    };
    const touchBlock = (e) => { if (dragging) e.preventDefault(); };
    const up = async () => {
      const d = this._drag;
      cleanup();
      if (!dragging || !d) return;
      this._suppressClick = true;
      setTimeout(() => { this._suppressClick = false; }, 50);
      d.ghost.remove();
      this.shadowRoot.querySelector(".app").classList.remove("dragging", "dragging-input");
      this._drag = null;
      if (!d.over) { this._render(); return; }
      const target = +d.over.dataset.drop;
      if (d.input) {
        if (target === 0) await this._clearInput(d.input).catch(() => {});
        else await this._moveInput(d.input, target).catch(() => {});
        this._render();
      } else {
        await this._routeSel(target, d.zones).catch(() => {});
      }
    };
    const cleanup = () => {
      clearTimeout(longTimer); cancelAnimationFrame(this._scrollRaf);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
      window.removeEventListener("touchmove", touchBlock);
    };
    if (touch) longTimer = setTimeout(() => { begin(); const g = this._drag.ghost; g.style.transform = `translate(${start.x + 12}px, ${start.y + 12}px)`; }, 280);
    window.addEventListener("pointermove", move, { passive: false });
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
    window.addEventListener("touchmove", touchBlock, { passive: false });
  }

  _autoScroll(y) {
    const sc = this.shadowRoot.querySelector(".content");
    if (!sc) return;
    const r = sc.getBoundingClientRect();
    const edge = 70;
    let speed = 0;
    if (y < r.top + edge) speed = -Math.ceil((r.top + edge - y) / 6);
    else if (y > r.bottom - edge) speed = Math.ceil((y - (r.bottom - edge)) / 6);
    cancelAnimationFrame(this._scrollRaf);
    if (speed) { sc.scrollTop += speed; this._scrollRaf = requestAnimationFrame(() => this._autoScroll(y)); }
  }
}

const STYLE = `
:host { display:block; height:100%; --pa-radius: var(--ha-card-border-radius, 12px); --pa-bg: var(--primary-background-color, #f4f5f7);
  --pa-card: var(--card-background-color, #fff); --pa-text: var(--primary-text-color, #1c1c1c); --pa-muted: var(--secondary-text-color, #6b6f76);
  --pa-line: var(--divider-color, rgba(0,0,0,.12)); --pa-accent: var(--primary-color, #03a9f4); --pa-err: var(--error-color, #db4437);
  --pa-ok: var(--success-color, #43a047); --pa-warn: var(--warning-color, #ffa600); font-family: var(--paper-font-body1_-_font-family, Roboto, system-ui, sans-serif); color: var(--pa-text); }
* { box-sizing: border-box; }
.app { display:flex; flex-direction:column; height:100%; background: var(--pa-bg); position:relative; }
.app.card { height: 720px; border-radius: var(--pa-radius); overflow:hidden; }
.app.dragging, .app.dragging * { cursor: grabbing !important; user-select:none; }
header { background: var(--app-header-background-color, var(--pa-card)); color: var(--app-header-text-color, var(--pa-text)); border-bottom:1px solid var(--pa-line); position:sticky; top:0; z-index:3; }
.top { display:flex; align-items:center; gap:10px; padding:8px 16px; min-height:56px; flex-wrap:wrap; }
.title { font-size:20px; font-weight:500; }
.unit-select { font-size:16px; padding:6px; border-radius:8px; border:1px solid var(--pa-line); background:var(--pa-card); color:var(--pa-text); }
nav { display:flex; gap:2px; padding:0 8px; overflow-x:auto; }
.tab { display:flex; align-items:center; gap:6px; padding:10px 14px; border:none; background:none; color:var(--pa-muted); font:inherit; font-weight:500; border-bottom:3px solid transparent; cursor:pointer; white-space:nowrap; }
.tab.active { color: var(--pa-accent); border-bottom-color: var(--pa-accent); }
.content { flex:1; overflow:auto; padding:16px; }
.i { width:20px; height:20px; fill: currentColor; flex: none; }
.i.big { width:40px; height:40px; }
.spacer { flex:1; }
.muted { color: var(--pa-muted); } .small { font-size:12px; } .pad { padding:12px; }
.pill { font-size:12px; padding:3px 10px; border-radius:20px; font-weight:500; }
.pill.ok { background: color-mix(in srgb, var(--pa-ok) 18%, transparent); color: var(--pa-ok); }
.pill.err { background: color-mix(in srgb, var(--pa-err) 18%, transparent); color: var(--pa-err); }
.badge { font-size:11px; padding:2px 7px; border-radius:10px; background: var(--pa-line); color: var(--pa-text); white-space:nowrap; font-weight:500; }
.badge.ok { background: color-mix(in srgb, var(--pa-ok) 20%, transparent); color: var(--pa-ok); }
.badge.warn { background: color-mix(in srgb, var(--pa-warn) 25%, transparent); color: color-mix(in srgb, var(--pa-warn) 70%, var(--pa-text)); }
.badge.err { background: color-mix(in srgb, var(--pa-err) 18%, transparent); color: var(--pa-err); }
.master { display:flex; align-items:center; gap:8px; }
.master .lbl { display:flex; align-items:center; gap:4px; color: var(--pa-muted); font-size:14px; }
.master input { width: 180px; }
.val { min-width:56px; font-variant-numeric: tabular-nums; font-size:13px; text-align:right; }
input[type=range] { accent-color: var(--pa-accent); }
.btn { display:inline-flex; align-items:center; gap:6px; padding:8px 14px; border-radius:20px; border:1px solid var(--pa-line); background: var(--pa-card); color: var(--pa-text); font: inherit; font-size:14px; font-weight:500; cursor:pointer; }
.btn:hover:not(:disabled) { border-color: var(--pa-accent); }
.btn:disabled { opacity:.45; cursor:default; }
.btn.small { padding:5px 10px; font-size:13px; } .btn.small .i { width:16px; height:16px; }
.btn.primary { background: var(--pa-accent); color: var(--text-primary-color, #fff); border-color: transparent; }
.btn.danger { color: var(--pa-err); border-color: color-mix(in srgb, var(--pa-err) 40%, transparent); }
.btn.ghost { border-color: transparent; background: transparent; }
.icon-btn { display:inline-flex; align-items:center; justify-content:center; width:40px; height:40px; border-radius:50%; border:none; background:transparent; color: var(--pa-muted); cursor:pointer; }
.icon-btn:hover { background: color-mix(in srgb, var(--pa-text) 8%, transparent); }
.icon-btn.on { color: var(--pa-ok); } .icon-btn.warn { color: var(--pa-err); }
.icon-btn.power.on { color: var(--pa-ok); } .icon-btn.power:not(.on) { color: var(--pa-err); }
.icon-btn.tiny { width:30px; height:30px; } .icon-btn.tiny .i { width:18px; height:18px; }
.toolbar { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:12px; }
.seg { display:inline-flex; border:1px solid var(--pa-line); border-radius:20px; overflow:hidden; background: var(--pa-card); }
.seg button { border:none; background:none; padding:6px 12px; font:inherit; font-size:13px; color: var(--pa-muted); cursor:pointer; }
.seg button.active { background: color-mix(in srgb, var(--pa-accent) 16%, transparent); color: var(--pa-accent); font-weight:500; }
.check { display:inline-flex; align-items:center; gap:6px; font-size:14px; cursor:pointer; }
.chips { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }
.chip { display:inline-flex; align-items:center; gap:6px; padding:6px 12px; border-radius:18px; border:1px solid var(--pa-line); background: var(--pa-card); color: var(--pa-text); font:inherit; font-size:13px; cursor:pointer; }
.chip.preset .i { color: var(--pa-accent); width:18px; height:18px; }
.chip:hover { border-color: var(--pa-accent); }
.hint { display:flex; align-items:center; gap:8px; color: var(--pa-muted); font-size:13px; margin-bottom:12px; }
.selbar { z-index:5 !important; display:flex; align-items:center; gap:8px; flex-wrap:wrap; padding:8px 12px; margin-bottom:12px; border-radius: var(--pa-radius); background: color-mix(in srgb, var(--pa-accent) 12%, var(--pa-card)); position:sticky; top:-16px; z-index:2; }
.selbar .count { font-weight:600; color: var(--pa-accent); margin-right:4px; }
.selbar .volgrp { display:inline-flex; align-items:center; gap:4px; } .selbar .volgrp input { width:110px; } .selbar .sr { display:none; }
.matrix { position:relative; display:grid; grid-template-columns: minmax(0,1fr) 90px minmax(0,1fr); align-items:start; }
svg.lines { position:absolute; left:0; top:0; pointer-events:none; z-index:0; overflow:visible; }
svg.lines path { fill:none; stroke-width:2.5; opacity:.75; }
svg.lines path.sel { stroke-width:4.5; opacity:1; } svg.lines path.off { stroke-dasharray:5 5; opacity:.4; }
.col { display:flex; flex-direction:column; gap:8px; position:relative; z-index:1; }
.col-head { font-size:13px; text-transform:uppercase; letter-spacing:.06em; color: var(--pa-muted); font-weight:600; padding:0 4px; }
.in-card, .out-card { background: var(--pa-card); border-radius: 10px; border:1px solid var(--pa-line); padding:8px 10px; box-shadow: var(--ha-card-box-shadow, none); transition: border-color .15s, box-shadow .15s, transform .15s, opacity .15s; }
.in-card { border-left: 5px solid var(--c); cursor: default; }
.in-card.active { box-shadow: 0 0 0 1px color-mix(in srgb, var(--c) 40%, transparent); }
.in-card .row, .out-card .row, .zone-card .row { display:flex; align-items:center; gap:6px; min-width:0; }
.nm { font-weight:500; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
.kind, .zn { font-size:11px; color: var(--pa-muted); background: color-mix(in srgb, var(--pa-text) 7%, transparent); border-radius:6px; padding:1px 5px; flex:none; }
.dot { width:10px; height:10px; border-radius:50%; background: var(--c); flex:none; display:inline-block; margin-right:4px; vertical-align:middle; }
.mini-chips { display:flex; flex-wrap:wrap; gap:4px; margin-top:6px; }
.mini { font-size:11px; padding:1px 7px; border-radius:8px; background: color-mix(in srgb, var(--c) 18%, transparent); }
.in-card.disconnect { border-left-color: var(--pa-muted); border-style:dashed; display:flex; align-items:center; gap:8px; color: var(--pa-muted); }
.in-card.drop-over { border-color: var(--c, var(--pa-accent)); box-shadow: 0 0 0 3px color-mix(in srgb, var(--c, var(--pa-accent)) 45%, transparent); transform: scale(1.02); }
.in-card.disconnect.drop-over { --c: var(--pa-err); }
.app.dragging .in-card:not(.drop-over) { opacity:.9; }
.out-card { border-left: 5px solid var(--c); cursor: grab; touch-action: pan-y; user-select:none; -webkit-user-select:none; }
.out-card .sub { margin-top:4px; font-size:12px; }
.out-card.selected { border-color: var(--pa-accent); box-shadow: 0 0 0 2px color-mix(in srgb, var(--pa-accent) 50%, transparent); }
.out-card.off { opacity:.6; } .out-card.lifted { opacity:.35; transform: scale(.98); }
.is-hidden { opacity:.5; }
.sel-box { width:20px; height:20px; border-radius:6px; border:2px solid var(--pa-line); display:inline-flex; align-items:center; justify-content:center; flex:none; color: var(--text-primary-color,#fff); background: var(--pa-card); padding:0; }
.selected .sel-box { background: var(--pa-accent); border-color: var(--pa-accent); }
.sel-box .i { width:14px; height:14px; } .btnlike { cursor:pointer; }
.src { display:inline-flex; align-items:center; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.src.none { color: var(--pa-muted); font-style: italic; }
.volbar { width:60px; height:6px; border-radius:3px; background: var(--pa-line); overflow:hidden; flex:none; }
.volbar span { display:block; height:100%; background: var(--pa-accent); }
.drag-ghost { position:fixed; left:0; top:0; z-index:20; pointer-events:none; display:flex; align-items:center; gap:6px; padding:8px 14px; border-radius:20px; background: var(--pa-accent); color: var(--text-primary-color,#fff); font-weight:500; box-shadow: 0 6px 20px rgba(0,0,0,.25); }
.grid { display:grid; gap:12px; }
.grid.zones { grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }
.zone-card { background: var(--pa-card); border-radius: var(--pa-radius); border:1px solid var(--pa-line); border-top:4px solid var(--c); padding:12px; display:flex; flex-direction:column; gap:10px; }
.zone-card.off { opacity:.65; } .zone-card.selected { box-shadow: 0 0 0 2px var(--pa-accent); }
.zone-card input[type=range] { flex:1; }
select, input[type=text] { font:inherit; padding:7px 9px; border-radius:8px; border:1px solid var(--pa-line); background: var(--pa-card); color: var(--pa-text); width:100%; }
.grid.presets { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
.preset-card { background: var(--pa-card); border-radius: var(--pa-radius); border:1px solid var(--pa-line); padding:12px; display:flex; flex-direction:column; gap:8px; position:relative; }
.preset-card .apply { padding-right:84px !important; display:flex; align-items:center; gap:10px; border:none; background: color-mix(in srgb, var(--pa-accent) 12%, transparent); color: var(--pa-text); border-radius:10px; padding:10px; font:inherit; font-size:16px; cursor:pointer; text-align:left; }
.preset-card .apply .i { color: var(--pa-accent); width:32px; height:32px; }
.preset-card .apply:hover { background: color-mix(in srgb, var(--pa-accent) 22%, transparent); }
.preset-card .desc { font-size:13px; display:flex; flex-direction:column; gap:3px; }
.preset-card .acts { position:absolute; top:12px; right:8px; display:flex; }
.preset-card .acts .icon-btn { width:32px; height:32px; background: var(--pa-card); }
.editor { background: var(--pa-card); border-radius: var(--pa-radius); padding:16px; border:1px solid var(--pa-line); }
.editor h2 { margin:0 0 12px; font-size:18px; }
.form { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:12px; margin-bottom:12px; }
.form label:not(.check) { display:flex; flex-direction:column; gap:4px; font-size:13px; color: var(--pa-muted); }
.form.opts { grid-template-columns: 1fr; gap:8px; margin-top:12px; }
.form.opts input[type=range] { width:160px; }
.ed-tools { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:10px; }
.ed-tools label:not(.check) { display:flex; align-items:center; gap:6px; } .ed-tools select { width:auto; min-width:180px; }
.grid.ed-zones { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap:6px; }
.ed-zone { display:flex; align-items:center; gap:8px; padding:8px; border-radius:8px; border:1px solid var(--pa-line); cursor:pointer; font-size:14px; flex-wrap:wrap; }
.ed-zone.on { border-color: var(--c, var(--pa-accent)); background: color-mix(in srgb, var(--c, var(--pa-accent)) 10%, transparent); }
.ed-zone select { width:100%; }
.actions { display:flex; justify-content:flex-end; gap:8px; margin-top:16px; }
.grid.status { grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
.card { background: var(--pa-card); border-radius: var(--pa-radius); border:1px solid var(--pa-line); padding:14px 16px; }
.card.wide { grid-column: 1 / -1; }
.card h3 { display:flex; align-items:center; gap:8px; margin:0 0 10px; font-size:15px; font-weight:600; }
.card h3 .i { color: var(--pa-accent); }
table { width:100%; border-collapse:collapse; font-size:14px; }
td, th { padding:6px 4px; text-align:left; vertical-align:middle; }
th { font-size:12px; color: var(--pa-muted); font-weight:600; border-bottom:1px solid var(--pa-line); }
table:not(.list) td:first-child { color: var(--pa-muted); width:45%; }
table.list tr + tr td { border-top:1px solid var(--pa-line); }
table.names td:first-child { width:48px; color: var(--pa-muted); } table.names td:last-child { width:48px; text-align:center; }
code { font-size:12px; background: color-mix(in srgb, var(--pa-text) 7%, transparent); padding:1px 5px; border-radius:4px; }
.settings-cols { display:grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap:12px; align-items:start; }
.kind-head { display:flex; align-items:center; gap:6px; margin:14px 0 4px; }
.banner { display:flex; align-items:center; gap:8px; padding:10px 14px; border-radius: 10px; margin-bottom:12px; }
.banner.err { background: color-mix(in srgb, var(--pa-err) 15%, transparent); color: var(--pa-err); }
.banner.warn { background: color-mix(in srgb, var(--pa-warn) 18%, transparent); }
.banner.small { padding:6px 10px; font-size:13px; margin:8px 0 0; }
.empty { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; padding:48px 16px; color: var(--pa-muted); text-align:center; }
.spinner { width:36px; height:36px; border:4px solid var(--pa-line); border-top-color: var(--pa-accent); border-radius:50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.modal-bg { position:absolute; inset:0; background: rgba(0,0,0,.4); display:flex; align-items:center; justify-content:center; z-index:30; }
.modal { background: var(--pa-card); border-radius: var(--pa-radius); padding:20px; width:min(420px, 92%); box-shadow: 0 10px 40px rgba(0,0,0,.3); }
.modal h3 { margin:0 0 8px; } .modal p { color: var(--pa-muted); margin:0; }
.toast-host { position:absolute; bottom:20px; left:50%; transform: translateX(-50%); z-index:40; pointer-events:none; }
.toast { background: #323232; color:#fff; padding:10px 18px; border-radius:8px; box-shadow: 0 4px 16px rgba(0,0,0,.3); font-size:14px; max-width: 80vw; }
.toast.error { background: var(--pa-err); }
.narrow .content { padding:10px; } .narrow .master input { width:110px; } .narrow .tab span { display:none; }
.narrow .kind { display:none; }
.ctl { display:inline-flex; flex:none; }
.narrow .out-card .sub { margin-top:2px; } .narrow .out-card .sub .src { font-size:12px; }
.narrow .out-card .icon-btn.tiny { width:26px; height:26px; }
.narrow .seg { max-width:100%; overflow-x:auto; } .seg button { white-space:nowrap; }
.narrow .matrix { grid-template-columns: minmax(0,1fr) 22px minmax(0,1.1fr); }
.narrow .in-card, .narrow .out-card { padding:6px 8px; font-size:14px; }
/* groups, compact, filters, undo */
.matrix .col.inputs { position: sticky; top: var(--sticky-top, 0px); max-height: calc(100vh - 150px - var(--sticky-top, 0px)); overflow-y: auto; overscroll-behavior: contain; padding: 2px 4px 8px 2px; scrollbar-width: thin; }
.app.card .matrix .col.inputs { max-height: 560px; }
.matrix .col.inputs .col-head { position: sticky; top: -2px; background: var(--pa-bg); z-index: 2; padding: 2px 4px 4px; }
.out-tools { display:flex; gap:6px; align-items:center; flex-wrap:wrap; }
.out-tools .seg button { padding:4px 10px; font-size:12px; }
input.search { font:inherit; font-size:13px; padding:5px 10px; border-radius:16px; border:1px solid var(--pa-line); background: var(--pa-card); color: var(--pa-text); flex:1; min-width:110px; width:auto; }
.toolbar input.search { flex: 0 1 180px; }
.link { border:none; background:none; color: var(--pa-accent); font:inherit; font-size:12px; cursor:pointer; padding:0 0 0 8px; text-transform:none; letter-spacing:0; }
.col-head { display:flex; align-items:center; gap:4px; }
.grp-head { display:flex; align-items:center; gap:6px; padding:6px 8px; margin-top:6px; border-radius:10px; background: color-mix(in srgb, var(--pa-text) 6%, var(--pa-card)); border:1px solid var(--pa-line); cursor: grab; user-select:none; -webkit-user-select:none; touch-action: pan-y; position:relative; z-index:1; }
.grp-head .nm { font-weight:600; }
.grp-head.selected { border-color: var(--pa-accent); }
.grp-head.lifted { opacity:.4; }
.grp-stats { font-size:12px; color: var(--pa-muted); white-space:nowrap; }
.grp-dots { display:inline-flex; gap:2px; } .grp-dots .dot { margin:0; width:9px; height:9px; }
.caret { border:none; background:none; color: var(--pa-muted); padding:0; display:inline-flex; cursor:pointer; }
.caret .i { transition: transform .15s; width:20px; height:20px; }
.grp-head.collapsed .caret .i { transform: rotate(-90deg); }
.grp-body { display:flex; flex-direction:column; gap:6px; padding-left:10px; border-left:2px solid var(--pa-line); margin-left:8px; }
.zone-grp { margin-bottom:14px; } .zone-grp .grp-head { margin-bottom:10px; cursor:pointer; }
.grp-acts { display:inline-flex; gap:2px; } .grp-acts .btn { padding:3px 8px; }
.matrix.compact .col { gap:4px; } .matrix.compact .grp-body { gap:4px; }
.out-card.compact { padding:4px 8px; } .out-card.compact .src { font-size:12px; color: var(--pa-muted); max-width:45%; }
.matrix.compact .in-card { padding:6px 10px; } .matrix.compact .mini-chips { margin-top:3px; }
.in-card .count { font-size:11px; font-weight:600; min-width:20px; text-align:center; padding:1px 6px; border-radius:10px; background: color-mix(in srgb, var(--c) 22%, transparent); }
.in-card .clear-in { opacity:.55; } .in-card .clear-in:hover { opacity:1; color: var(--pa-err); }
.in-card.draggable { cursor: grab; touch-action: pan-y; user-select:none; -webkit-user-select:none; }
.in-card.lifted { opacity:.4; }
.mini.more { background: var(--pa-line); font-weight:600; }
.app.dragging-input .in-card.disconnect { border-color: var(--pa-err); color: var(--pa-err); background: color-mix(in srgb, var(--pa-err) 8%, var(--pa-card)); animation: pulse 1.2s ease-in-out infinite; }
@keyframes pulse { 50% { box-shadow: 0 0 0 4px color-mix(in srgb, var(--pa-err) 25%, transparent); } }
.drag-ghost.input { background: var(--c); }
svg.lines path.grp { stroke-width:5; opacity:.55; }
.toast { display:flex; align-items:center; gap:14px; pointer-events:auto; }
.toast-btn { border:none; background:none; color: var(--pa-accent, #4fc3f7); font:inherit; font-weight:600; text-transform:uppercase; letter-spacing:.04em; cursor:pointer; padding:2px 4px; }
.toast-btn { color: #82cfff; }
.groups-card { margin-bottom:12px; }
.grp-row { display:flex; align-items:center; gap:6px; margin-bottom:6px; }
.nowrap { white-space:nowrap; }
.grp-sel select { padding:4px 6px; font-size:13px; }
.chip.on { border-color: var(--pa-accent); background: color-mix(in srgb, var(--pa-accent) 12%, var(--pa-card)); }
.ed-groups { align-items:center; }
.narrow .presets-row { flex-wrap:nowrap; overflow-x:auto; padding-bottom:4px; scrollbar-width:none; } .narrow .presets-row .chip { flex:none; }
.narrow .grp-stats { display:none; } .narrow .grp-acts .btn { padding:3px 5px; }
.narrow .out-card.compact .dot { margin-right:2px; }
.narrow .in-card .count { display:none; }
.narrow .in-card .clear-in { width:22px; height:22px; } .narrow .in-card .clear-in .i { width:16px; height:16px; }
.narrow .out-card.compact [data-a="zone-mute"]:not(.warn) { display:none; }
.narrow .out-card.compact .icon-btn.tiny { width:24px; height:24px; }
.narrow .sel-box { width:16px; height:16px; } .narrow .row { gap:4px; }
.narrow .in-card, .narrow .out-card { padding:6px 6px 6px 7px; }
.narrow .content { padding:8px 6px; }
.narrow .matrix { grid-template-columns: minmax(0,1fr) 12px minmax(0,1.15fr); }
.narrow .mini { font-size:10px; padding:1px 5px; }
/* neo additions */
.hdr-status { display:inline-flex; align-items:center; gap:4px; font-size:13px; color: var(--pa-ok); } .hdr-status.warn { color: var(--pa-warn); }
.hdr-status .i, .hdr-temp .i { width:16px; height:16px; }
.hdr-temp { display:inline-flex; align-items:center; gap:2px; font-size:13px; color: var(--pa-muted); } .hdr-temp.warn { color: var(--pa-err); }
.icon-btn.tv.on { color: var(--pa-ok); } .icon-btn.tv.off { color: var(--pa-muted); }
.tvtxt { font-size:11px; color: var(--pa-muted); white-space:nowrap; } .tvtxt.ok { color: var(--pa-ok); }
.warn-txt { color: var(--pa-err); }
.dot.err-dot { --c: var(--pa-err); width:8px; height:8px; margin:0 2px; }
.badge .i { width:12px; height:12px; vertical-align:-2px; margin-right:2px; }
.matrix.locked .out-card, .matrix.locked .in-card { cursor: default; } .matrix.locked { opacity:.85; }
.summary-row { display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:10px; margin-bottom:12px; }
.stat { background: var(--pa-card); border:1px solid var(--pa-line); border-radius: var(--pa-radius); padding:10px 14px; display:flex; flex-direction:column; }
.stat b { font-size:24px; font-weight:600; } .stat span { color: var(--pa-muted); font-size:13px; }
.stat.warn b { color: var(--pa-warn); } .stat.err b { color: var(--pa-err); }
.lbl-sel { display:flex; flex-direction:column; gap:3px; font-size:12px; color: var(--pa-muted); }
.facts { display:grid; grid-template-columns: 1fr 1fr; gap:6px 12px; font-size:13px; }
.facts > div { display:flex; flex-direction:column; min-width:0; } .facts b { font-weight:500; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.facts b.ok { color: var(--pa-ok); }
.zone-card .acts .btn { padding:4px 10px; }
.hdbt-list { display:flex; flex-direction:column; gap:12px; }
.card.hdbt.poor { border-left:4px solid var(--pa-warn); } .card.hdbt.down { border-left:4px solid var(--pa-err); }
.hdbt-head { display:flex; align-items:center; gap:8px; margin-bottom:10px; } .hdbt-head .nm { font-size:16px; font-weight:600; }
.hdbt-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:14px; }
.hdbt-grid h4 { margin:0 0 6px; font-size:12px; text-transform:uppercase; letter-spacing:.05em; color: var(--pa-muted); }
.mse-rows { display:flex; flex-direction:column; gap:5px; margin-bottom:4px; }
.mse-row { display:grid; grid-template-columns: 38px 1fr; align-items:center; gap:6px; font-size:12px; color: var(--pa-muted); }
.mse { position:relative; height:16px; border-radius:4px; background: color-mix(in srgb, var(--pa-text) 6%, transparent); overflow:hidden; display:block; }
.mse > span { position:absolute; left:0; top:0; bottom:0; border-radius:4px; }
.mse.good > span { background: color-mix(in srgb, var(--pa-ok) 55%, transparent); } .mse.meh > span { background: color-mix(in srgb, var(--pa-warn) 60%, transparent); } .mse.bad > span { background: color-mix(in srgb, var(--pa-err) 60%, transparent); }
.mse > i { position:absolute; left:75%; top:0; bottom:0; border-left:2px dashed var(--pa-err); opacity:.7; }
.mse > em { position:absolute; right:6px; top:0; font-style:normal; font-size:11px; line-height:16px; color: var(--pa-text); }
.mse.none { background:none; color: var(--pa-muted); }
.kv { display:flex; justify-content:space-between; gap:10px; font-size:13px; padding:3px 0; border-bottom:1px dashed var(--pa-line); }
.kv span { color: var(--pa-muted); } .kv b { font-weight:500; text-align:right; overflow-wrap:anywhere; }
.temp-row { display:grid; grid-template-columns: 70px 1fr 50px; align-items:center; gap:8px; font-size:13px; margin:4px 0; }
.tbar { height:8px; border-radius:4px; background: var(--pa-line); overflow:hidden; } .tbar span { display:block; height:100%; background: var(--pa-ok); }
.tbar.warm span { background: var(--pa-warn); } .tbar.hot span { background: var(--pa-err); }
.modal.wide-modal { width:min(760px, 94%); max-height:86vh; overflow:auto; display:flex; flex-direction:column; gap:10px; }
.modal h3 .dot { width:12px; height:12px; }
.ed-zone.pick { text-align:left; background: var(--pa-card); color: var(--pa-text); font:inherit; }
.ed-zone.pick .sel-box { color:#fff; } .ed-zone.pick.on .sel-box { background: var(--c); border-color: var(--c); }
.ed-zone.pick.already { opacity:.6; cursor:default; } .ed-zone.pick.already .sel-box { background: var(--pa-muted); border-color: var(--pa-muted); }
input.edited { border-color: var(--pa-accent); background: color-mix(in srgb, var(--pa-accent) 7%, var(--pa-card)); }
.narrow .facts { grid-template-columns: 1fr; } .narrow .tvtxt { display:none; }
`;

customElements.get("neo-matrix-panel") || customElements.define("neo-matrix-panel", class extends NeoApp {});
customElements.get("neo-matrix-card") || customElements.define("neo-matrix-card", class extends NeoApp {});
window.customCards = window.customCards || [];
if (!window.customCards.find((c) => c.type === "neo-matrix-card"))
  window.customCards.push({ type: "neo-matrix-card", name: "Pulse-Eight neo Matrix", description: "Video routing, outputs, HDBaseT links and status for a neo matrix." });
