import { appendToFormData } from "./forms";

describe("forms utils", () => {
  describe("appendToFormData", () => {
    let formData: FormData;

    beforeEach(() => {
      formData = new FormData();
    });

    it("should append simple string value", () => {
      appendToFormData("name", "John", formData);
      expect(formData.get("name")).toBe("John");
    });

    it("should append undefined as empty string", () => {
      appendToFormData("undefinedField", undefined, formData);
      expect(formData.get("undefinedField")).toBe("");
    });

    it("should append null as empty string", () => {
      appendToFormData("nullField", null, formData);
      expect(formData.get("nullField")).toBe("");
    });

    it("should append value for defined falsy values", () => {
      appendToFormData("falsyField", 0, formData);
      expect(formData.get("falsyField")).toBe("0");
    });

    it("should append empty array with null value", () => {
      appendToFormData("emptyArray", [], formData);
      expect(formData.get("emptyArray[]")).toBe("");
    });

    it("should append array of primitive values", () => {
      appendToFormData("numbers", [1, 2, 3], formData);
      expect(formData.get("numbers[0]")).toBe("1");
      expect(formData.get("numbers[1]")).toBe("2");
      expect(formData.get("numbers[2]")).toBe("3");
    });

    it("should append array of objects with nested properties", () => {
      const data = [
        { name: "John", age: 30 },
        { name: "Jane", age: 25 },
      ];

      appendToFormData("users", data, formData);

      expect(formData.get("users[0].name")).toBe("John");
      expect(formData.get("users[0].age")).toBe("30");
      expect(formData.get("users[1].name")).toBe("Jane");
      expect(formData.get("users[1].age")).toBe("25");
    });

    it("should append array of files", () => {
      const file1 = new File(["content1"], "file1.txt");
      const file2 = new File(["content2"], "file2.txt");

      appendToFormData("files", [file1, file2], formData);

      expect(formData.get("files[0]")).toBe(file1);
      expect(formData.get("files[1]")).toBe(file2);
    });
  });
});
