"""Generador configurable de matrices numéricas para exploración y clustering."""
import argparse
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler, RobustScaler, StandardScaler


def comprobar_claves(obj, permitidas, contexto):
    desconocidas = set(obj) - set(permitidas)
    if desconocidas:
        raise ValueError(f'{contexto}: opciones desconocidas {sorted(desconocidas)}')


def generar(dataset, config, salida):
    comprobar_claves(config, ['id', 'contexto', 'variables', 'escalado', 'pca'], 'Configuración')
    id_col = config.get('id', 'cod_ine')
    specs = config.get('variables', {})
    if not isinstance(specs, dict) or not specs or id_col in specs:
        raise ValueError('Define variables numéricas; el identificador no puede entrar en el cálculo.')
    contexto = config.get('contexto', [])
    if not isinstance(contexto, list) or len(contexto) != len(set(contexto)):
        raise ValueError('contexto debe ser una lista sin duplicados.')
    if set(contexto) & (set(specs) | {id_col}):
        raise ValueError('Los campos de contexto deben ser distintos del ID y de las variables.')
    df = pd.read_csv(dataset, dtype={id_col: str})
    faltan = set([id_col] + contexto + list(specs)) - set(df.columns)
    if faltan:
        raise ValueError(f'Faltan columnas en el dataset: {sorted(faltan)}')
    if df.empty or df[id_col].isna().any() or not df[id_col].is_unique:
        raise ValueError('El dataset debe tener filas e identificadores únicos y no vacíos.')
    if id_col == 'cod_ine' and not df[id_col].str.fullmatch(r'\d{5}', na=False).all():
        raise ValueError('cod_ine debe tener cinco dígitos, conservando los ceros iniciales.')
    X = df[list(specs)].apply(pd.to_numeric, errors='raise')
    if np.isinf(X.to_numpy()).any():
        raise ValueError('Hay valores infinitos; revisar el dataset.')
    for col, spec in specs.items():
        if not isinstance(spec, dict):
            raise ValueError(f'{col}: se esperaba un objeto de configuración.')
        comprobar_claves(spec, ['ausentes', 'valor', 'transformacion', 'recorte'], col)
        if spec.get('ausentes', 'error') not in ['error', 'eliminar_filas', 'mediana', 'media', 'maximo', 'constante']:
            raise ValueError(f'{col}: tratamiento de ausentes desconocido.')
        if spec.get('transformacion', 'ninguna') not in ['ninguna', 'log1p', 'sqrt']:
            raise ValueError(f'{col}: transformación desconocida.')
        recorte = spec.get('recorte')
        if recorte is not None and (not isinstance(recorte, list) or len(recorte) != 2 or not 0 <= recorte[0] < recorte[1] <= 1):
            raise ValueError(f'{col}: recorte debe ser [cuantil_inferior, cuantil_superior] entre 0 y 1.')
    # Eliminar primero; todas las estadísticas se ajustan sobre las filas retenidas.
    eliminar = pd.Series(False, index=df.index)
    for col, spec in specs.items():
        if spec.get('ausentes', 'error') == 'eliminar_filas':
            eliminar |= X[col].isna()
    indices = df.index[~eliminar]
    if len(indices) < 2:
        raise ValueError('Quedan menos de dos municipios después de eliminar ausencias.')
    originales = X.loc[indices].copy()
    preparada = originales.copy()
    mascara = originales.isna()
    parametros = {}
    for col, spec in specs.items():
        metodo = spec.get('ausentes', 'error')
        serie = preparada[col]
        relleno = None
        if serie.isna().any():
            if metodo == 'error':
                raise ValueError(f'{col}: {serie.isna().sum()} ausencias. Elige un tratamiento explícito.')
            if metodo in ['mediana', 'media', 'maximo']:
                relleno = float({'mediana': serie.median, 'media': serie.mean, 'maximo': serie.max}[metodo]())
            elif metodo == 'constante':
                relleno = float(spec['valor'])
            if relleno is None or not np.isfinite(relleno):
                raise ValueError(f'{col}: no se puede calcular un relleno válido.')
            preparada[col] = serie.fillna(relleno)
        parametros[col] = {'relleno_aplicado': relleno}
    transformada = preparada.copy()
    for col, spec in specs.items():
        transformacion = spec.get('transformacion', 'ninguna')
        serie = transformada[col]
        if transformacion == 'log1p':
            if (serie <= -1).any():
                raise ValueError(f'{col}: log1p requiere valores mayores que -1.')
            serie = np.log1p(serie)
        elif transformacion == 'sqrt':
            if (serie < 0).any():
                raise ValueError(f'{col}: sqrt requiere valores no negativos.')
            serie = np.sqrt(serie)
        recorte = spec.get('recorte')
        if recorte is not None:
            limites = serie.quantile(recorte).tolist()
            serie = serie.clip(*limites)
            parametros[col]['limites_recorte_transformado'] = limites
        transformada[col] = serie
    constantes = transformada.columns[transformada.nunique() <= 1].tolist()
    if constantes:
        raise ValueError(f'Variables constantes tras el tratamiento: {constantes}. Retíralas o revisa la configuración.')
    nombre_scaler = config.get('escalado', 'standard')
    scalers = {'standard': StandardScaler, 'robust': RobustScaler, 'minmax': MinMaxScaler}
    if nombre_scaler not in [*scalers, 'ninguno']:
        raise ValueError('escalado debe ser standard, robust, minmax o ninguno.')
    scaler = scalers[nombre_scaler]() if nombre_scaler != 'ninguno' else None
    matriz = pd.DataFrame(scaler.fit_transform(transformada) if scaler else transformada.to_numpy(), columns=list(specs), index=indices)
    if not np.isfinite(matriz.to_numpy()).all():
        raise ValueError('La matriz contiene valores no finitos.')
    pca_config = config.get('pca', None)
    pca, componentes = None, None
    if pca_config is not None:
        if isinstance(pca_config, bool):
            raise ValueError('pca debe ser null, un entero o una fracción entre 0 y 1.')
        if isinstance(pca_config, int):
            if not 1 <= pca_config <= min(matriz.shape):
                raise ValueError('Número de componentes PCA fuera de rango.')
        elif not isinstance(pca_config, float) or not 0 < pca_config < 1:
            raise ValueError('pca debe ser null, un entero o una fracción entre 0 y 1.')
        pca = PCA(n_components=pca_config, svd_solver='full')
        componentes = pd.DataFrame(pca.fit_transform(matriz), index=indices, columns=[f'PC{i+1}' for i in range(pca.n_components_)])
    def con_id(tabla):
        return pd.concat([df.loc[tabla.index, [id_col]], tabla], axis=1)
    tablas = {
        'matriz_original.csv': con_id(originales),
        'matriz_imputada.csv': con_id(preparada),
        'matriz_transformada.csv': con_id(transformada),
        'matriz_ml.csv': con_id(matriz),
        'mascara_imputaciones.csv': con_id(mascara.add_prefix('imputado__')),
        'municipios.csv': df.loc[indices, [id_col] + contexto],
        'filas_excluidas.csv': df.loc[eliminar, [id_col]].assign(motivo='Ausencia en variable configurada para eliminar filas'),
    }
    if componentes is not None:
        tablas['matriz_pca.csv'] = con_id(componentes)
    resumen = {
        'dataset': str(dataset), 'sha256_dataset': hashlib.sha256(Path(dataset).read_bytes()).hexdigest(),
        'configuracion': config, 'filas_entrada': len(df), 'filas_matriz': len(indices),
        'filas_excluidas': int(eliminar.sum()), 'ausencias_entrada': X.isna().sum().to_dict(),
        'valores_imputados': mascara.sum().to_dict(), 'parametros_variables': parametros,
        'entorno': {'python': platform.python_version(), 'pandas': pd.__version__, 'numpy': np.__version__, 'scikit_learn': sklearn.__version__},
        'scaler': {k: getattr(scaler, k).tolist() for k in ['mean_', 'scale_', 'center_', 'min_', 'data_min_', 'data_max_'] if hasattr(scaler, k)} if scaler else None,
        'pca': {'componentes': pca.components_.tolist(), 'media': pca.mean_.tolist(), 'varianza_explicada': pca.explained_variance_ratio_.tolist(), 'varianza_acumulada': float(pca.explained_variance_ratio_.sum())} if pca else None,
    }
    # Validar todo antes de crear la entrega. Nunca sobrescribir otra prueba.
    salida = Path(salida)
    if salida.exists():
        raise ValueError(f'La salida ya existe: {salida}. Elige otra carpeta para esta prueba.')
    salida.mkdir(parents=True)
    for nombre, tabla in tablas.items():
        tabla.to_csv(salida / nombre, index=False, encoding='utf-8-sig')
    (salida / 'informe.json').write_text(json.dumps(resumen, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(f'Matriz generada: {len(indices)} filas, {len(specs)} variables. Carpeta: {salida}')
    if pca:
        print(f'PCA: {pca.n_components_} componentes; varianza conservada: {pca.explained_variance_ratio_.sum():.2%}')
    return resumen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True, help='CSV consolidado de entrada')
    parser.add_argument('--config', required=True, help='Archivo JSON de configuración')
    parser.add_argument('--salida', required=True, help='Carpeta nueva para esta prueba')
    args = parser.parse_args()
    try:
        config = json.loads(Path(args.config).read_text(encoding='utf-8-sig'))
        generar(args.dataset, config, args.salida)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f'ERROR: {error}\n')


if __name__ == '__main__':
    main()
