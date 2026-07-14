// Contenido de la ayuda contextual por pantalla (RF de capacitación al usuario).
// Un solo lugar para editar/ampliar los textos. Español, orientado a "cómo se
// hace bien el proceso" y a "qué errores evitar".

export interface ContenidoAyuda {
  titulo: string
  intro: string
  pasos: string[]
  errores?: string[]
  consejo?: string
}

export const AYUDA = {
  resumen: {
    titulo: 'Resumen',
    intro: 'Vista rápida del estado de la natillera: los saldos de los dos fondos.',
    pasos: [
      'Revisa el saldo del Fondo de Ahorro (el dinero de la gente) y del Fondo de Rentabilidad (las ganancias).',
      'Usa el menú de la izquierda para cada operación.',
      'Cambia de natillera con el selector de arriba.',
    ],
    errores: ['Los saldos se calculan solos desde los movimientos; no se editan a mano.'],
  },
  natillera: {
    titulo: 'Natillera',
    intro: 'Aquí creas la natillera, ajustas su configuración y avanzas su estado.',
    pasos: [
      'Crea la natillera con su nombre y las fechas del ciclo.',
      'Define la cuota, las tasas de préstamo, los topes y la estrategia de reparto.',
      'Avanza el estado: ABIERTA y luego EN_OPERACION para poder operar.',
    ],
    errores: [
      'El estado solo avanza, nunca retrocede.',
      'Hasta llegar a EN_OPERACION no puedes recaudar cuotas ni prestar.',
    ],
    consejo: 'Cambiar la configuración rige hacia futuro; no recalcula lo ya cobrado.',
  },
  participantes: {
    titulo: 'Participantes',
    intro: 'Inscribe a las personas que ahorran en la natillera.',
    pasos: [
      'Llena nombre, documento, fecha de ingreso y el valor de su cuota (viene prellenado con el de la natillera).',
      'Pulsa Inscribir.',
      'Haz clic en un nombre para ver su estado de cuenta y ajustar su cuota.',
    ],
    errores: [
      'No puede haber dos participantes con el mismo documento.',
      'Un participante no se borra: si se retira, márcalo como Retirado y conserva su historial.',
    ],
    consejo: 'Cada persona puede tener su propia cuota mensual; el valor de la config es solo el por defecto.',
  },
  participante_detalle: {
    titulo: 'Detalle del participante',
    intro: 'Estado de cuenta de una persona y sus operaciones individuales.',
    pasos: [
      'Consulta sus ahorros y todos sus movimientos.',
      'Ajusta su cuota mensual si es distinta a la de los demás.',
      'Paga la cuota de un período o registra un aporte extraordinario.',
      'Cambia su estado (Activo, Suspendido o Retirado).',
    ],
    errores: ['Los aportes extraordinarios deben estar habilitados en la configuración.'],
  },
  recaudo: {
    titulo: 'Recaudo de cuotas',
    intro: 'Cobro de la cuota de ahorro a varias personas a la vez.',
    pasos: [
      'Elige el período que estás cobrando.',
      'Marca con el interruptor a quienes pagaron.',
      'Revisa el total (suma de las cuotas de los marcados) y pulsa Registrar.',
    ],
    errores: [
      'El monto no se escribe: es la cuota propia de cada persona (o el valor por defecto si no tiene una).',
      'Si marcas a alguien que ya pagó ese período, se omite (no cobra doble).',
    ],
    consejo: 'Para cobrarle a una sola persona, hazlo desde su detalle en Participantes.',
  },
  prestamos: {
    titulo: 'Préstamos',
    intro: 'Presta dinero del Fondo de Ahorro; solo el interés es ganancia.',
    pasos: [
      'Solicita: participante, capital, tasa y plazo.',
      'Aprueba y luego Desembolsa (el capital sale del ahorro).',
      'Registra los abonos: la app separa sola el capital del interés.',
    ],
    errores: [
      'El capital vuelve íntegro al ahorro; nunca genera utilidad.',
      'Respeta los topes de préstamos y de capital por persona.',
      'Usa “Detectar mora” para marcar los préstamos vencidos.',
    ],
  },
  multas: {
    titulo: 'Multas',
    intro: 'Sanciones que, al pagarse, aumentan el Fondo de Rentabilidad.',
    pasos: [
      'Crea las multas en el catálogo (tipo y valor).',
      'Imponer: elige participante, la multa y el motivo.',
      'Registra el pago; o anula una multa impuesta.',
    ],
    errores: [
      'Solo la multa PAGADA suma a la rentabilidad.',
      'Una multa ya pagada no se anula; se corrige con una reversión.',
    ],
  },
  actividades: {
    titulo: 'Actividades',
    intro: 'Pollas, rifas y eventos cuya utilidad va al Fondo de Rentabilidad.',
    pasos: [
      'Crea la actividad (tipo Polla: valor por número y cantidad).',
      'Abre su detalle para asignar números y gestionarla.',
    ],
    errores: [
      'El premio NO se digita: es el pozo (valor por número × números pagados) y se lo lleva el ganador.',
      'El fondo solo gana cuando no hay ganador (número no pagado): ahí el pozo pasa a rentabilidad.',
    ],
  },
  actividad_detalle: {
    titulo: 'Detalle de la actividad',
    intro: 'Gestión de una polla: números, pagos, sorteo y cierre.',
    pasos: [
      'Asigna números a los participantes y abre la actividad.',
      'Marca los pagos haciendo clic en cada número.',
      'Registra gastos, ejecuta el Sorteo y luego Cierra la actividad.',
    ],
    errores: [
      'Solo los números PAGADOS participan en el sorteo.',
      'Si el número ganador no está pagado, no hay ganador y toda la utilidad va a rentabilidad.',
      'Clonar copia números y participantes, pero no los pagos ni el sorteo.',
    ],
  },
  reportes: {
    titulo: 'Reportes',
    intro: 'Saldos de los fondos y rentabilidad por fuente; exportable a Excel.',
    pasos: [
      'Revisa los indicadores de los dos fondos.',
      'Analiza la rentabilidad por fuente (intereses, actividades, multas).',
      'Exporta a Excel si lo necesitas.',
    ],
    errores: ['La rentabilidad nunca incluye el retorno de capital de préstamos.'],
  },
  liquidacion: {
    titulo: 'Liquidación',
    intro: 'Cierre del ciclo: devuelve los ahorros y reparte la rentabilidad.',
    pasos: [
      'Lleva la natillera a “Pendiente de liquidación” (en Natillera).',
      'Inicia y revisa los bloqueos; luego Calcula el reparto.',
      'Confirma escribiendo el nombre exacto de la natillera y descarga el acta.',
    ],
    errores: [
      'Es IRREVERSIBLE una vez confirmada: revisa bien el cálculo antes.',
      'No se puede liquidar con préstamos sin pagar o actividades abiertas.',
    ],
  },
  usuarios: {
    titulo: 'Usuarios y accesos',
    intro: 'Da acceso a otras personas y define su rol en la natillera.',
    pasos: [
      'Agrega a la persona con su correo y una contraseña temporal.',
      'Elige el rol; si es Cliente, vincúlalo a un participante.',
      'Puedes cambiar el rol, reiniciar la clave o quitar el acceso.',
    ],
    errores: [
      'Administrador: todo. Supervisor: casi toda la gestión, menos crear la natillera, liquidarla y gestionar usuarios. Cliente: solo lee lo suyo.',
      'No puedes dejar la natillera sin ningún administrador.',
    ],
  },
} satisfies Record<string, ContenidoAyuda>

export type TemaAyuda = keyof typeof AYUDA
