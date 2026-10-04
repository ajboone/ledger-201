export interface OrderReconciliation {
  order_id: number;
  square_order_id: string | null;
  order_total_amount: number;
  completed_payment_amount: number;
  completed_refund_amount: number;
  net_collected_amount: number;
  difference: number;
  status: "RECONCILED" | "REVIEW_REQUIRED";
}

export interface ItemSummary {
  item_name: string;
  quantity_sold: number;
  gross_sales_amount: number;
  total_sales_amount: number;
}

export interface DailyReview {
  location_id: number;
  location_name: string;
  currency: string;
  review_date: string;
  order_count: number;
  subtotal_amount: number;
  discount_amount: number;
  tax_amount: number;
  service_charge_amount: number;
  order_total_amount: number;
  completed_payment_amount: number;
  completed_refund_amount: number;
  net_collected_amount: number;
  average_order_value: number;
  reconciliation_difference: number;
  reconciliation_status: "RECONCILED" | "REVIEW_REQUIRED";
  orders: OrderReconciliation[];
  top_items: ItemSummary[];
}
