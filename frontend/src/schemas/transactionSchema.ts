import { z } from "zod";

/**
 * Transaction type enum (BUY / SELL / DEPOSIT / WITHDRAWAL).
 * Matches the backend transaction types.
 */
export const transactionTypeEnum = z.enum(["BUY", "SELL", "DEPOSIT", "WITHDRAWAL"]);
export type TransactionType = z.infer<typeof transactionTypeEnum>;

/**
 * Price mode toggle used in the create / edit transaction forms.
 */
export const priceModeEnum = z.enum(["market", "manual"]);
export type PriceMode = z.infer<typeof priceModeEnum>;

/**
 * Income type enum (DIVIDEND / INTEREST).
 */
export const incomeTypeEnum = z.enum(["DIVIDEND", "INTEREST"]);
export type IncomeType = z.infer<typeof incomeTypeEnum>;

/**
 * Helper: validates that a date string is not in the future.
 */
const notFutureDateString = (value: string) => {
  if (!value) return true;
  const selected = new Date(value);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return selected.getTime() <= today.getTime();
};

/**
 * Schema for the "Add transaction" form.
 *
 * Form inputs are strings (from <input> / FormattedNumberInput), so numeric
 * fields use z.coerce.number() to convert before validating.
 */
export const transactionFormSchema = z
  .object({
    asset_id: z.string().min(1, "Vui lòng chọn tài sản"),
    type: transactionTypeEnum,
    quantity: z.coerce.number({ message: "Số lượng phải là số" }).positive("Số lượng phải lớn hơn 0"),
    price: z.coerce.number({ message: "Giá phải là số" }),
    price_mode: priceModeEnum,
    fee: z.coerce.number({ message: "Phí phải là số" }).min(0, "Phí không được âm"),
    date: z
      .string()
      .min(1, "Ngày là bắt buộc")
      .refine(notFutureDateString, "Ngày không được trong tương lai"),
    notes: z.string(),
  })
  .refine(
    (data) => {
      // Price is only required when entering a manual price.
      if (data.price_mode === "manual") {
        return data.price > 0;
      }
      return true;
    },
    {
      message: "Giá phải lớn hơn 0",
      path: ["price"],
    }
  );

export type TransactionFormValues = z.infer<typeof transactionFormSchema>;

/**
 * String-based input shape for the create-transaction form.
 *
 * Form inputs (text / FormattedNumberInput) produce strings, so numeric
 * fields are typed as strings here. The zod schema uses z.coerce.number()
 * to coerce these strings during validation.
 */
export interface TransactionFormInput {
  asset_id: string;
  type: TransactionType;
  quantity: string;
  price: string;
  price_mode: PriceMode;
  fee: string;
  date: string;
  notes: string;
}

/**
 * Schema for the "Edit transaction" modal form.
 *
 * Editing does not allow changing the asset or type, only quantity / price /
 * fee / date / notes.
 */
export const transactionEditSchema = z
  .object({
    quantity: z.coerce.number({ message: "Số lượng phải là số" }).positive("Số lượng phải lớn hơn 0"),
    price: z.coerce.number({ message: "Giá phải là số" }),
    price_mode: priceModeEnum,
    fee: z.coerce.number({ message: "Phí phải là số" }).min(0, "Phí không được âm"),
    date: z
      .string()
      .min(1, "Ngày là bắt buộc")
      .refine(notFutureDateString, "Ngày không được trong tương lai"),
    notes: z.string(),
  })
  .refine(
    (data) => {
      if (data.price_mode === "manual") {
        return data.price > 0;
      }
      return true;
    },
    {
      message: "Giá phải lớn hơn 0",
      path: ["price"],
    }
  );

export type TransactionEditValues = z.infer<typeof transactionEditSchema>;

/**
 * String-based input shape for the edit-transaction modal form.
 */
export interface TransactionEditInput {
  quantity: string;
  price: string;
  price_mode: PriceMode;
  fee: string;
  date: string;
  notes: string;
}

/**
 * Schema for the "Add income" form.
 */
export const incomeFormSchema = z.object({
  asset_id: z.string().min(1, "Vui lòng chọn tài sản"),
  type: incomeTypeEnum,
  amount: z.coerce.number({ message: "Số tiền phải là số" }).positive("Số tiền phải lớn hơn 0"),
  date: z
    .string()
    .min(1, "Ngày là bắt buộc")
    .refine(notFutureDateString, "Ngày không được trong tương lai"),
  notes: z.string(),
});

export type IncomeFormValues = z.infer<typeof incomeFormSchema>;

/**
 * String-based input shape for the add-income form.
 */
export interface IncomeFormInput {
  asset_id: string;
  type: IncomeType;
  amount: string;
  date: string;
  notes: string;
}
