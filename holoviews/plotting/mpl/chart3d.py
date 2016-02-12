import numpy as np
import param
import matplotlib.cm as cm

from ...core import Dimension
from ...core.util import match_spec, basestring
from ..util import map_colors
from .element import ColorbarPlot
from .chart import PointPlot


class Plot3D(ColorbarPlot):
    """
    Plot3D provides a common baseclass for mplot3d based
    plots.
    """

    azimuth = param.Integer(default=-60, bounds=(-180, 180), doc="""
        Azimuth angle in the x,y plane.""")

    elevation = param.Integer(default=30, bounds=(0, 180), doc="""
        Elevation angle in the z-axis.""")

    distance = param.Integer(default=10, bounds=(7, 15), doc="""
        Distance from the plotted object.""")

    disable_axes = param.Boolean(default=False, doc="""
        Disable all axes.""")

    bgcolor = param.String(default='white', doc="""
        Background color of the axis.""")

    projection = param.ObjectSelector(default='3d', doc="""
        The projection of the matplotlib axis.""")

    show_frame = param.Boolean(default=False, doc="""
        Whether to draw a frame around the figure.""")

    show_grid = param.Boolean(default=True, doc="""
        Whether to draw a grid in the figure.""")

    xaxis = param.ObjectSelector(default='fixed',
                                 objects=['fixed', None], doc="""
        Whether and where to display the xaxis.""")

    yaxis = param.ObjectSelector(default='fixed',
                                 objects=['fixed', None], doc="""
        Whether and where to display the yaxis.""")

    zaxis = param.ObjectSelector(default='fixed',
                                 objects=['fixed', None], doc="""
        Whether and where to display the yaxis.""")

    def _finalize_axis(self, key, **kwargs):
        """
        Extends the ElementPlot _finalize_axis method to set appropriate
        labels, and axes options for 3D Plots.
        """
        axis = self.handles['axis']
        self.handles['fig'].set_frameon(False)
        axis.grid(self.show_grid)
        axis.view_init(elev=self.elevation, azim=self.azimuth)
        axis.dist = self.distance

        if self.xaxis is None:
            axis.w_xaxis.line.set_lw(0.)
            axis.w_xaxis.label.set_text('')
        if self.yaxis is None:
            axis.w_yaxis.line.set_lw(0.)
            axis.w_yaxis.label.set_text('')
        if self.zaxis is None:
            axis.w_zaxis.line.set_lw(0.)
            axis.w_zaxis.label.set_text('')
        if self.disable_axes:
            axis.set_axis_off()

        axis.set_axis_bgcolor(self.bgcolor)
        return super(Plot3D, self)._finalize_axis(key, **kwargs)


    def _draw_colorbar(self, artist, element, dim=None):
        fig = self.handles['fig']
        ax = self.handles['axis']
        # Get colorbar label
        if dim is None:
            dim = element.vdims[0]

        elif not isinstance(dim, Dimension):
            dim = element.get_dimension(dim)
        label = str(dim)
        cbar = fig.colorbar(artist, shrink=0.7, ax=ax)
        self.handles['cax'] = cbar.ax
        self._adjust_cbar(cbar, label, dim)



class Scatter3DPlot(Plot3D, PointPlot):
    """
    Subclass of PointPlot allowing plotting of Points
    on a 3D axis, also allows mapping color and size
    onto a particular Dimension of the data.
    """

    color_index = param.ClassSelector(default=4, class_=(basestring, int),
                                      allow_None=True, doc="""
      Index of the dimension from which the color will the drawn""")

    size_index = param.ClassSelector(default=3, class_=(basestring, int),
                                     allow_None=True, doc="""
      Index of the dimension from which the sizes will the drawn.""")

    def initialize_plot(self, ranges=None):
        axis = self.handles['axis']
        points = self.hmap.last
        ranges = self.compute_ranges(self.hmap, self.keys[-1], ranges)
        ranges = match_spec(points, ranges)
        key = self.keys[-1]
        xs, ys, zs = (points.dimension_values(i) for i in range(3))

        style = self.style[self.cyclic_index]
        cdim = points.get_dimension(self.color_index)
        if cdim and 'cmap' in style:
            cs = points.dimension_values(self.color_index)
            style['c'] = cs
            if 'clim' not in style:
                clims = ranges[cdim.name]
                style.update(vmin=clims[0], vmax=clims[1])
        if points.get_dimension(self.size_index):
            style['s'] = self._compute_size(points, style)

        scatterplot = axis.scatter(xs, ys, zs, zorder=self.zorder, **style)

        self.handles['axis'].add_collection(scatterplot)
        self.handles['artist'] = scatterplot

        return self._finalize_axis(key, ranges=ranges)

    def update_handles(self, axis, points, key, ranges=None):
        artist = self.handles['artist']
        artist._offsets3d = tuple(points[d] for d in points.dimensions())
        cdim = points.get_dimension(self.color_index)
        style = self.style[self.cyclic_index]
        if cdim and 'cmap' in style:
            cs = points.dimension_values(self.color_index)
            clim = style['clim'] if 'clim' in style else ranges[cdim.name]
            cmap = cm.get_cmap(style['cmap'])
            artist._facecolor3d = map_colors(cs, clim, cmap, False)
        if points.get_dimension(self.size_index):
            artist.set_sizes(self._compute_size(points, style))




class SurfacePlot(Plot3D):
    """
    Plots surfaces wireframes and contours in 3D space.
    Provides options to switch the display type via the
    plot_type parameter has support for a number of
    styling options including strides and colors.
    """

    colorbar = param.Boolean(default=False, doc="""
        Whether to add a colorbar to the plot.""")

    plot_type = param.ObjectSelector(default='surface',
                                     objects=['surface', 'wireframe',
                                              'contour'], doc="""
        Specifies the type of visualization for the Surface object.
        Valid values are 'surface', 'wireframe' and 'contour'.""")

    style_opts = ['antialiased', 'cmap', 'color', 'shade',
                  'linewidth', 'facecolors', 'rstride', 'cstride']

    def initialize_plot(self, ranges=None):
        element = self.hmap.last
        key = self.keys[-1]

        ranges = self.compute_ranges(self.hmap, self.keys[-1], ranges)
        ranges = match_spec(element, ranges)

        self.update_handles(self.handles['axis'], element, key, ranges)
        return self._finalize_axis(key, ranges=ranges)


    def update_handles(self, axis, element, key, ranges=None):
        if 'artist' in self.handles:
            self.handles['axis'].collections.remove(self.handles['artist'])
        mat = element.data
        rn, cn = mat.shape
        l, b, zmin, r, t, zmax = self.get_extents(element, ranges)
        r, c = np.mgrid[l:r:(r-l)/float(rn), b:t:(t-b)/float(cn)]

        style_opts = self.style[self.cyclic_index]

        if self.plot_type == "wireframe":
            self.handles['artist'] = self.handles['axis'].plot_wireframe(r, c, mat, **style_opts)
        elif self.plot_type == "surface":
            style_opts['vmin'] = zmin
            style_opts['vmax'] = zmax
            self.handles['artist'] = self.handles['axis'].plot_surface(r, c, mat, **style_opts)
        elif self.plot_type == "contour":
            self.handles['artist'] = self.handles['axis'].contour3D(r, c, mat, **style_opts)



class TrisurfacePlot(Plot3D):
    """
    Plots a trisurface given a Trisurface element, containing
    X, Y and Z coordinates.
    """

    colorbar = param.Boolean(default=False, doc="""
        Whether to add a colorbar to the plot.""")

    style_opts = ['cmap', 'color', 'shade', 'linewidth', 'edgecolor']

    def initialize_plot(self, ranges=None):
        element = self.hmap.last
        key = self.keys[-1]

        ranges = self.compute_ranges(self.hmap, self.keys[-1], ranges)
        ranges = match_spec(element, ranges)

        self.update_handles(self.handles['axis'], element, key, ranges)
        return self._finalize_axis(key, ranges=ranges)


    def update_handles(self, axis, element, key, ranges=None):
        if 'artist' in self.handles:
            self.handles['axis'].collections.remove(self.handles['artist'])
        style_opts = self.style[self.cyclic_index]
        dims = element.dimensions(label=True)
        vrange = ranges[dims[2]]
        x, y, z = [element.dimension_values(d) for d in dims]
        artist = axis.plot_trisurf(x, y, z, vmax=vrange[1],
                                   vmin=vrange[0], **style_opts)
        self.handles['artist'] = artist
