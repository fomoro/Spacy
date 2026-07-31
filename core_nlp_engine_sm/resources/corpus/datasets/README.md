# Datasets para modelos

Esta carpeta se reserva para el material utilizado al desarrollar modelos estadísticos:

- `entrenamiento/`: datos con los que aprende el modelo.
- `validacion/`: datos para ajustar hiperparámetros, umbrales y decisiones de diseño.
- `prueba/`: datos finales que no se consultan ni modifican durante el desarrollo.

El benchmark conocido no pertenece aquí. Vive en `../benchmarks/customer_intent_benchmark.json` y se utiliza para medir el sistema, no como fuente de entrenamiento.

Cuando se implemente `TextCategorizerService`, sus particiones deberán crearse bajo `text_categorizer/`. Solo deben contener datos autorizados, curados y anonimizados.
