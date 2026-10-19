import { describe, expect, it } from "vitest";
import { languageName } from "./languages";
import { basename, parentName } from "./paths";

describe("names", () => {
  it("takes a path's file name and its folder's, either slash", () => {
    expect(basename("D:\\Séries\\Saison 1\\S01E01.mkv")).toBe("S01E01.mkv");
    expect(basename("/home/marc/S01E01.mkv")).toBe("S01E01.mkv");
    expect(parentName("D:\\Séries\\Saison 1\\S01E01.mkv")).toBe("Saison 1");
    expect(parentName("/home/marc/S01E01.mkv")).toBe("marc");
    expect(parentName("S01E01.mkv")).toBe("");
  });

  // In the tests' DOM, the system is in English.
  it("names the languages it knows, keeps the others' codes", () => {
    expect(languageName("fre")).toBe("French");
    expect(languageName("fra")).toBe("French");
    expect(languageName("tha")).toBe("tha");
    expect(languageName(null)).toBe("unknown language");
  });
});
