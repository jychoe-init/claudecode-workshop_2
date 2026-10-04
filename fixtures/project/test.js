import assert from "node:assert/strict";
import { getUserPlan } from "./src/userService.js";
assert.equal(getUserPlan(1), "pro");
assert.equal(getUserPlan(2), "free");
assert.equal(getUserPlan(3), "unknown");
assert.equal(getUserPlan(999), "unknown");
console.log("PASS: 4 behavior checks");
