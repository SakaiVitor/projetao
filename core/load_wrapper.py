from panda3d.core import Material, ColorAttrib, CollisionNode, CollisionSphere, BitMask32


def load_model_with_default_material(loader, path: str):
    model = loader.loadModel(path)
    model.setTwoSided(True)

    # Material leve, só para reflexão sem sobrescrever vertex color
    material = Material()
    material.setShininess(20)
    model.setMaterial(material, 1)

    # Ativa cor por vértice
    model.setAttrib(ColorAttrib.makeVertex())

    # Colisão esférica automática no centro do bounding volume
    bounds = model.getTightBounds()
    min_pt, max_pt = bounds
    center = (min_pt + max_pt) * 0.5
    radius = (max_pt - min_pt).length() * 0.5

    coll_node = CollisionNode(f"collision_{path}")
    coll_node.addSolid(CollisionSphere(center, radius))
    coll_nodepath = model.attachNewNode(coll_node)
    coll_nodepath.setCollideMask(BitMask32.bit(1))

    return model
