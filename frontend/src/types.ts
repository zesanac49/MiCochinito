// Tipos de los contratos de la API (doc 07). Los montos llegan como string
// decimal (TEC-01): nunca se hace aritmética con ellos en el cliente (doc 08 §4).

export type Rol = 'ADMINISTRADOR' | 'SUPERVISOR' | 'CLIENTE'

export interface Membresia {
  natillera_uuid: string
  natillera_nombre: string
  rol: Rol
}

export interface Usuario {
  uuid: string
  email: string
  nombre: string
  membresias: Membresia[]
}

export interface Tokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Miembro {
  usuario_uuid: string
  nombre: string
  email: string
  rol: Rol
  activo: boolean
  participante_uuid: string | null
  participante_nombre: string | null
}

export type EstadoNatillera =
  | 'BORRADOR'
  | 'ABIERTA'
  | 'EN_OPERACION'
  | 'PENDIENTE_LIQUIDACION'
  | 'LIQUIDADA'
  | 'ARCHIVADA'

export interface Natillera {
  uuid: string
  nombre: string
  estado: EstadoNatillera
  ciclo_inicio: string
  ciclo_fin: string
}

export type EstadoParticipante = 'ACTIVO' | 'SUSPENDIDO' | 'RETIRADO'
export type TipoDocumento = 'CC' | 'CE' | 'TI' | 'PP'

export interface Participante {
  uuid: string
  nombre: string
  tipo_documento: TipoDocumento
  numero_documento: string
  estado: EstadoParticipante
  fecha_ingreso: string
  telefono?: string | null
  direccion?: string | null
  // Cuota mensual propia. Si es null, se usa el valor por defecto de la config.
  valor_cuota?: string | null
}

export interface Periodo {
  uuid: string
  anio: number
  mes: number
  fecha_limite_cuota: string | null
  conciliado: boolean
}

export interface Asiento {
  uuid: string
  creado_en: string
  fondo: 'AHORRO' | 'RENTABILIDAD'
  naturaleza: 'DEBITO' | 'CREDITO'
  concepto: string
  monto: string
  descripcion: string
  origen_tipo: string
  origen_id: number
  participante_id?: number | null
}

export interface Fondo {
  tipo: 'AHORRO' | 'RENTABILIDAD'
  saldo: string
}

export interface ItemLoteResultado {
  participante_uuid: string
  periodo_uuid: string
  estado: 'PAGADO' | 'YA_PAGADO' | 'NO_ENCONTRADO'
  asiento_uuid: string | null
}

export interface ResumenLote {
  cantidad_pagados: number
  total_recaudado: string
  items: ItemLoteResultado[]
}

export type EstadoPrestamo =
  | 'SOLICITADO'
  | 'APROBADO'
  | 'RECHAZADO'
  | 'DESEMBOLSADO'
  | 'EN_PAGO'
  | 'EN_MORA'
  | 'PAGADO'

export interface Prestamo {
  uuid: string
  estado: EstadoPrestamo
  capital: string
  tasa: string
  plazo_meses: number
  saldo_capital: string
  fecha_desembolso: string | null
  motivo_rechazo: string | null
}

export interface Descomposicion {
  capital: string
  interes: string
  total: string
}

export interface PagoPrestamoResultado {
  descomposicion: Descomposicion
  prestamo: Prestamo
  asientos: Asiento[]
}

export type EstadoMulta = 'IMPUESTA' | 'PAGADA' | 'ANULADA'

export interface Multa {
  uuid: string
  estado: EstadoMulta
  valor: string
  motivo: string
  justificacion_anulacion: string | null
}

export interface CatalogoMulta {
  uuid: string
  nombre: string
  tipo: string
  valor: string
  activo: boolean
}

export type TipoActividad = 'POLLA' | 'RIFA' | 'BINGO' | 'BAZAR' | 'VENTA' | 'OTRO'
export type EstadoActividad = 'BORRADOR' | 'ABIERTA' | 'SORTEADA' | 'CERRADA'
export type TipoMovimiento = 'INGRESO' | 'GASTO' | 'PREMIO'

export interface NumeroActividad {
  numero: number
  participante_id: number
  pagado: boolean
}

export interface MovimientoActividad {
  tipo: TipoMovimiento
  concepto: string
  valor: string
}

export interface SorteoActividad {
  numero_ganador: number
  hubo_ganador: boolean
  participante_ganador_id: number | null
  fuente: string
}

export interface Actividad {
  uuid: string
  tipo: TipoActividad
  nombre: string
  estado: EstadoActividad
  valor_numero: string | null
  cantidad_numeros: number | null
  premio: string | null
  fecha_sorteo: string | null
  utilidad: string
  numeros: NumeroActividad[]
  movimientos: MovimientoActividad[]
  sorteo: SorteoActividad | null
}

export interface BloqueoLiquidacion {
  tipo: string
  origen_tipo: string
  origen_id: number
  descripcion: string
}

export interface DetalleLiquidacion {
  participante_uuid: string
  participante_nombre: string
  ahorros: string
  participacion_rentabilidad: string
  capital_pendiente: string
  intereses_pendientes: string
  multas_pendientes: string
  saldo_final: string
}

export interface Liquidacion {
  uuid: string | null
  fase: 'PRE_VALIDACION' | 'CALCULADA' | 'EN_REVISION' | 'CONFIRMADA' | 'ACTA_GENERADA'
  estrategia_aplicada: string | null
  saldo_rentabilidad_distribuido: string
  detalles: DetalleLiquidacion[]
  bloqueos: BloqueoLiquidacion[]
}

export interface Dashboard {
  fondos: { tipo: string; saldo: string }[]
  rentabilidad_por_fuente: Record<string, string>
}

export interface CuentaParticipante {
  participante_uuid: string
  saldos: {
    ahorros: string
    intereses_pendientes: string
    multas_pendientes: string
  }
  asientos: Asiento[]
}

export interface ErrorApi {
  error: {
    codigo: string
    mensaje: string
    detalle: Record<string, unknown>
    request_id: string
  }
}
