import centers from '../../data/centers.csv?raw'
import branches from '../../data/branches.csv?raw'
import vehicles from '../../data/vehicles.csv?raw'
import orders from '../../data/delivery_orders.csv?raw'
import { readDeliveryDataset } from '../services/delivery-csv'

export function createDeliveryData() {
  return readDeliveryDataset({ centers, branches, vehicles, orders })
}
