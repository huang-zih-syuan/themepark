import os

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)


@app.route('/', methods=['GET'])
def index():
    return send_from_directory('.', 'index.html')


@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        data = request.json
        graph = data.get('graph', {})
        start_node = str(data.get('startNode', ''))
        constraints = data.get('constraints', {})

        limits = {
            'time': float(constraints.get('W_time', 9999)),
            'budget': float(constraints.get('W_cost', 9999)),
            'stamina': float(constraints.get('W_stamina', 9999)),
            'satisfaction_min': float(constraints.get('W_satisfaction_min', 1)),
            'thrill_max': float(constraints.get('W_thrill_max', 10))
        }

        vertices = {
            str(v['id']): {
                'time': float(v.get('W_time', 0)),
                'budget': float(v.get('W_cost', 0)),
                'stamina': float(v.get('W_stamina', 0)),
                'satisfaction': float(v.get('W_satisfaction', 1)),
                'thrill': float(v.get('W_thrill', 1))
            }
            for v in graph.get('vertices', [])
        }

        if start_node not in vertices:
            return jsonify({"success": False, "message": "起點不存在"})

        adj = {u: [] for u in vertices}
        for edge in graph.get('edges', []):
            u, v = str(edge['source']), str(edge['target'])
            w_time = float(edge.get('w_time', 0))
            adj[u].append({'to': v, 'time': w_time})
            adj[v].append({'to': u, 'time': w_time})

        def edge_time(src, dst):
            for edge in adj.get(src, []):
                if edge['to'] == dst:
                    return edge['time']
            return None

        def passes_node_filter(node_id):
            node = vertices[node_id]
            return (
                node['satisfaction'] >= limits['satisfaction_min'] and
                node['thrill'] <= limits['thrill_max']
            )

        start_data = vertices[start_node]
        if not passes_node_filter(start_node):
            return jsonify({
                "success": False,
                "message": "起點不符合滿意度或刺激度限制，請重新選擇起點或放寬條件。"
            })

        initial_res = {
            'time': start_data['time'],
            'budget': start_data['budget'],
            'stamina': start_data['stamina']
        }

        if (
            initial_res['time'] > limits['time'] or
            initial_res['budget'] > limits['budget'] or
            initial_res['stamina'] > limits['stamina']
        ):
            return jsonify({"success": False, "message": "起點本身已超過資源限制。"})

        best_tour = []
        max_visit = -1
        best_metrics = {}

        def dfs(curr, path, visited, res):
            nonlocal best_tour, max_visit, best_metrics

            # Strict simple cycle rule: the final return must be a real edge.
            return_time = edge_time(curr, start_node)
            if return_time is not None:
                closed_time = res['time'] + return_time
                if closed_time <= limits['time'] and len(path) > max_visit:
                    max_visit = len(path)
                    best_tour = list(path) + [start_node]
                    best_metrics = {
                        'time': closed_time,
                        'budget': res['budget'],
                        'stamina': res['stamina']
                    }

            for edge in adj.get(curr, []):
                nxt = edge['to']
                if nxt in visited:
                    continue

                if not passes_node_filter(nxt):
                    continue

                nxt_data = vertices[nxt]
                new_res = {
                    'time': res['time'] + edge['time'] + nxt_data['time'],
                    'budget': res['budget'] + nxt_data['budget'],
                    'stamina': res['stamina'] + nxt_data['stamina']
                }

                if (
                    new_res['time'] <= limits['time'] and
                    new_res['budget'] <= limits['budget'] and
                    new_res['stamina'] <= limits['stamina']
                ):
                    visited.add(nxt)
                    path.append(nxt)
                    dfs(nxt, path, visited, new_res)
                    path.pop()
                    visited.remove(nxt)

        dfs(start_node, [start_node], {start_node}, initial_res)

        if max_visit != -1:
            return jsonify({"success": True, "tour": best_tour, "metrics": best_metrics})

        return jsonify({"success": False, "message": "無可行路徑，請放寬限制或新增回到起點的連線。"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
