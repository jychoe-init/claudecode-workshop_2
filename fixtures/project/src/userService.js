import { users } from "./users.js";
export function getUser(id) { return users.find(user => user.id === id); }
export function getUserPlan(id) { return getUser(id)?.profile?.plan ?? "unknown"; }
