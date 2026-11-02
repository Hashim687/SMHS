import {post} from "./api";

const loadRzp = () => new Promise((ok, no) => {
  if (window.Razorpay) return ok();
  const s = document.createElement("script");
  s.src = "https://checkout.razorpay.com/v1/checkout.js";
  s.onload = ok;
  s.onerror = no;
  document.body.appendChild(s);
});

export async function payLab(oref, who, title, onDone, onFail) {
  const r = await post(`/api/public/lab-orders/${oref}/pay`, {});
  if (r.status !== 201) return onFail(r.status === 503 ? "unavailable" : "payFail");
  const o = r.data;
  const verify = async (oid, pid, sig) => {
    const v = await post(`/api/public/lab-orders/${oref}/verify`, {razorpay_order_id: oid, razorpay_payment_id: pid, razorpay_signature: sig});
    v.status === 200 ? onDone() : onFail("payFail");
  };
  if (o.mock) return verify(o.order_id, o.mock_payment_id, o.mock_signature);
  try {
    await loadRzp();
    new window.Razorpay({
      key: o.key_id, order_id: o.order_id, amount: o.amount, currency: "INR", name: title,
      prefill: {name: who.name, contact: who.phone},
      handler: x => verify(x.razorpay_order_id, x.razorpay_payment_id, x.razorpay_signature)
    }).open();
  } catch { onFail("unavailable"); }
}
