export interface SquareSalesReportImportRequest {
  location_id: number;
  raw_report_text: string;
}

export interface SquareSalesReportImportResult {
  report_id: number;
  report_start: string;
  report_end: string;
  categories_imported: number;
  items_imported: number;
  discounts_imported: number;
  warnings: string[];
}

export interface SquareCategorySales {
  id: number;
  category_name: string;
  quantity: number;
  sales_amount: number;
}

export interface SquareItemSales {
  id: number;
  item_name: string;
  variation_name: string | null;
  quantity: number;
  sales_amount: number;
}

export interface SquareDiscountSummary {
  id: number;
  discount_name: string;
  usage_count: number;
  amount: number;
}

export interface SquareSalesReportSummary {
  id: number;
  location_id: number;
  report_start: string;
  report_end: string;
  report_name: string | null;
  reported_at: string | null;
  source_name: string;
  gross_sales_amount: number;
  item_sales_amount: number;
  service_charge_amount: number;
  returns_amount: number;
  discount_comp_amount: number;
  net_sales_amount: number;
  tax_amount: number;
  tips_amount: number;
  gift_card_sales_amount: number;
  refund_amount: number;
  total_amount: number;
  total_collected_amount: number;
  fees_amount: number;
  net_total_amount: number;
  created_at: string;
}

export interface SquareSalesReportDetail extends SquareSalesReportSummary {
  category_sales: SquareCategorySales[];
  item_sales: SquareItemSales[];
  discount_summaries: SquareDiscountSummary[];
}
