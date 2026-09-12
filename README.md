# ShopApi
api para integración con tiendas de shopify

## Pedidos

La aplicación de Shopify debe tener el permiso `read_orders`.

```http
GET /api/v1/orders?first=50&search=1045&status=todos
GET /api/v1/orders/1045
```

Estados disponibles para el filtro: `todos`, `pagado`, `pendiente`,
`preparando`, `enviado`, `entregado` y `cancelado`.

Ambos endpoints son de solo lectura. El listado devuelve el ID numérico que se
debe enviar al endpoint de detalle.
